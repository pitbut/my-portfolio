package com.robutpit.pitbrowser.agents

import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.time.Duration

/**
 * Агент на любом ИИ с OpenAI-совместимым Chat Completions API: ChatGPT, Gemini, Grok, DeepSeek, Qwen,
 * свой сервер (Ollama, vLLM, LM Studio) и любой новый сервис с таким API.
 * Встроенного веб-поиска у них нет: поиск делается через Claude (если есть его ключ), страницы читает браузер.
 */
class OpenAiEngine(
    private val provider: Provider,
    private val apiKey: String,
    private val http: OkHttpClient = defaultClient,
) : Engine {

    class ApiException(val code: Int, message: String) : Exception(message)

    private val base = provider.baseUrl.trimEnd('/')

    /** Список моделей сервиса (только те, что подходят для текста/чата). */
    fun listModels(): List<String> {
        val body = request("GET", "$base/models", null)
        val data = body.optJSONArray("data") ?: body.optJSONArray("models") ?: JSONArray()
        return (0 until data.length())
            .mapNotNull { data.optJSONObject(it)?.let { m -> m.optString("id").ifBlank { m.optString("name") } } }
            .map { it.removePrefix("models/") }
            .filter { id -> NOT_CHAT.none { id.lowercase().contains(it) } }
            .distinct()
            .sorted()
    }

    fun checkKey() { listModels() }

    override fun run(agent: Agent, task: String, ctx: RunContext): AgentRun {
        val model = agent.model.ifBlank { provider.model }
        val run = AgentRun(agent.id, System.currentTimeMillis(), model = model, provider = provider.id, title = agent.name)
        run.costKnown = false // цены других сервисов браузер не знает — показываем токены
        if (model.isBlank()) {
            run.status = "error"
            run.error = "для ${provider.name} не выбрана модель — выберите её в разделе «ИИ»"
            run.finished = System.currentTimeMillis()
            return run
        }
        val messages = JSONArray()
            .put(JSONObject().put("role", "system").put("content", AgentPrompts.system(agent, ctx.helpers)))
            .put(JSONObject().put("role", "user").put("content", task))
        var tools: JSONArray? = JSONArray().apply {
            ToolExecutor.specs(agent, ctx.helpers, withSearchAndFetch = true).forEach { (name, description, schema) ->
                put(JSONObject().put("type", "function").put("function",
                    JSONObject().put("name", name).put("description", description).put("parameters", schema)))
            }
        }.takeIf { it.length() > 0 }
        val executor = ToolExecutor(agent, ctx, run)

        try {
            for (iteration in 1..MAX_ITERATIONS) {
                if (ctx.cancel.get()) { run.status = "stopped"; break }
                val req = JSONObject().put("model", model).put("messages", messages)
                if (tools != null) req.put("tools", tools)
                val resp = try {
                    request("POST", "$base/chat/completions", req)
                } catch (e: ApiException) {
                    // некоторые модели не умеют инструменты — тогда работаем без них
                    if (e.code == 400 && tools != null && iteration == 1 && (e.message ?: "").let { m -> m.contains("tool", true) || m.contains("function", true) }) {
                        tools = null
                        synchronized(run) { run.steps += ToolExecutor.step("tool", "модель не поддерживает инструменты — отвечает без поиска") }
                        continue
                    }
                    throw e
                }
                resp.optJSONObject("usage")?.let { u ->
                    synchronized(run) {
                        run.inputTokens += u.optLong("prompt_tokens", u.optLong("input_tokens"))
                        run.outputTokens += u.optLong("completion_tokens", u.optLong("output_tokens"))
                    }
                }
                val choice = resp.optJSONArray("choices")?.optJSONObject(0) ?: throw ApiException(0, "пустой ответ сервиса")
                val msg = choice.optJSONObject("message") ?: JSONObject()
                val calls = msg.optJSONArray("tool_calls")
                ctx.onStep(run)

                if (calls != null && calls.length() > 0) {
                    // назад отправляем только роль, текст и вызовы (без служебного «рассуждения» — его не все принимают)
                    messages.put(JSONObject().put("role", "assistant").put("content", msg.opt("content") ?: JSONObject.NULL).put("tool_calls", calls))
                    val parsed = (0 until calls.length()).map { i ->
                        val c = calls.getJSONObject(i)
                        val f = c.optJSONObject("function") ?: JSONObject()
                        val args = runCatching { JSONObject(f.optString("arguments").ifBlank { "{}" }) }.getOrDefault(JSONObject())
                        ToolCall(c.optString("id").ifBlank { "call_$i" }, f.optString("name"), args)
                    }
                    for (o in executor.execute(parsed)) {
                        messages.put(JSONObject().put("role", "tool").put("tool_call_id", o.id).put("content", o.text))
                    }
                    ctx.onStep(run)
                    continue
                }
                when (choice.optString("finish_reason")) {
                    "content_filter" -> { run.status = "refused"; run.error = "сервис отказался отвечать (фильтр содержимого)" }
                    else -> {
                        run.result = textOf(msg.opt("content"))
                        run.status = "done"
                        if (choice.optString("finish_reason") == "length") run.result += "\n\n(ответ обрезан: слишком длинный)"
                    }
                }
                break
            }
            if (run.status == "running") {
                run.status = "error"
                run.error = "агент сделал $MAX_ITERATIONS шагов и не закончил — уточните задачу"
            }
        } catch (e: ApiException) {
            run.status = "error"
            run.error = errorText(e)
        } catch (e: Exception) {
            run.status = "error"
            run.error = "нет связи с ${provider.name}: ${e.message?.take(200)}"
        }
        run.finished = System.currentTimeMillis()
        ctx.onStep(run)
        return run
    }

    private fun textOf(content: Any?): String = when (content) {
        is String -> content.trim()
        is JSONArray -> (0 until content.length()).mapNotNull { content.optJSONObject(it)?.optString("text") }.joinToString("\n").trim()
        else -> ""
    }

    private fun errorText(e: ApiException) = when (e.code) {
        401 -> "неверный ключ ${provider.name}"
        402 -> "на счёте ${provider.name} закончились деньги"
        403 -> "у ключа ${provider.name} нет доступа к этой модели"
        404 -> "модель или адрес не найдены у ${provider.name} — проверьте модель в разделе «ИИ»"
        429 -> "${provider.name}: слишком много запросов или исчерпан лимит — попробуйте позже"
        else -> "ошибка ${provider.name} (${e.code}): ${e.message?.take(300)}"
    }

    private fun request(method: String, url: String, body: JSONObject?): JSONObject {
        val b = Request.Builder().url(url)
            .header("Authorization", "Bearer $apiKey")
            .header("User-Agent", "PitBrowser-Agent/1.0")
        if (body != null) b.method(method, body.toString().toRequestBody(JSON)) else b.get()
        http.newCall(b.build()).execute().use { r ->
            val text = r.body?.string().orEmpty()
            if (!r.isSuccessful) {
                val msg = runCatching { JSONObject(text).let { j -> j.optJSONObject("error")?.optString("message") ?: j.optString("message") } }
                    .getOrNull()?.ifBlank { null } ?: text.take(300)
                throw ApiException(r.code, msg)
            }
            return runCatching { JSONObject(text) }.getOrElse { throw ApiException(r.code, "ответ сервиса — не JSON") }
        }
    }

    companion object {
        const val MAX_ITERATIONS = 12
        private val JSON = "application/json".toMediaType()
        private val defaultClient = OkHttpClient.Builder()
            .connectTimeout(Duration.ofSeconds(20))
            .readTimeout(Duration.ofMinutes(5))
            .build()

        /** Модели не для текста: картинки, звук, эмбеддинги, модерация. */
        private val NOT_CHAT = listOf("embed", "tts", "whisper", "dall-e", "image", "audio", "moderation", "transcribe", "realtime", "search-preview", "veo", "imagen", "rerank")
    }
}
