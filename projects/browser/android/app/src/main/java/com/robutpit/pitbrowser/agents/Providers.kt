package com.robutpit.pitbrowser.agents

import org.json.JSONArray
import org.json.JSONObject
import java.io.File

/**
 * ИИ-сервис, с которым умеют работать агенты.
 * kind = "anthropic" — Claude через официальный SDK; "openai" — любой сервис с OpenAI-совместимым
 * Chat Completions API (ChatGPT, Gemini, Grok, DeepSeek, Qwen, свой сервер с Ollama/vLLM и т.п.).
 */
data class Provider(
    val id: String,
    val name: String,
    val kind: String,
    val baseUrl: String,
    val builtIn: Boolean,
    /** Модель по умолчанию — выбирается пользователем из списка, который отдаёт сам сервис. */
    val model: String,
    val keysUrl: String = "",
) {
    fun toJson(): JSONObject = JSONObject()
        .put("id", id).put("name", name).put("kind", kind).put("baseUrl", baseUrl)
        .put("builtIn", builtIn).put("model", model).put("keysUrl", keysUrl)

    companion object {
        const val CLAUDE = "claude"

        /** Встроенные сервисы. Адреса можно поменять в настройках сервиса, если компания их сменит. */
        val PRESETS = listOf(
            Provider(CLAUDE, "Claude (Anthropic)", "anthropic", "https://api.anthropic.com", true, "claude-opus-5-5", "platform.claude.com"),
            Provider("openai", "ChatGPT (OpenAI)", "openai", "https://api.openai.com/v1", true, "", "platform.openai.com"),
            Provider("gemini", "Gemini (Google)", "openai", "https://generativelanguage.googleapis.com/v1beta/openai", true, "", "aistudio.google.com"),
            Provider("grok", "Grok (xAI)", "openai", "https://api.x.ai/v1", true, "", "console.x.ai"),
            Provider("deepseek", "DeepSeek", "openai", "https://api.deepseek.com/v1", true, "", "platform.deepseek.com"),
            Provider("qwen", "Qwen (Alibaba Cloud)", "openai", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1", true, "", "bailian.console.alibabacloud.com"),
        )

        private val ID = Regex("^[a-z0-9][a-z0-9-]{1,30}$")

        fun parse(o: JSONObject) = Provider(
            o.getString("id"), o.optString("name"), o.optString("kind", "openai"), o.optString("baseUrl"),
            o.optBoolean("builtIn"), o.optString("model"), o.optString("keysUrl"),
        )

        /** Проверка своего сервиса из формы. */
        fun custom(o: JSONObject): Provider {
            val name = o.optString("name").trim().take(40).ifEmpty { throw IllegalArgumentException("укажите название ИИ") }
            val base = o.optString("baseUrl").trim().trimEnd('/')
            if (!base.startsWith("https://") && !base.startsWith("http://")) throw IllegalArgumentException("адрес API должен начинаться с https://")
            val id = o.optString("id").ifEmpty {
                "custom-" + name.lowercase().map { if (it in 'a'..'z' || it in '0'..'9') it else '-' }.joinToString("")
                    .replace(Regex("-+"), "-").trim('-').take(20).ifEmpty { "ai" }
            }
            if (!ID.matches(id)) throw IllegalArgumentException("неверный id сервиса")
            return Provider(id, name, "openai", base, false, o.optString("model").trim().take(100))
        }
    }
}

/** Список сервисов: встроенные (с правками пользователя) + свои. Ключи — отдельно, в KeyVault. */
class ProviderStore(dir: File) {
    private val file = File(dir.apply { mkdirs() }, "providers.json")

    @Synchronized fun all(): List<Provider> {
        val saved = runCatching { JSONArray(file.readText()) }.getOrDefault(JSONArray())
        val byId = (0 until saved.length()).map { Provider.parse(saved.getJSONObject(it)) }.associateBy { it.id }
        // встроенные — всегда в начале и в своём порядке; из сохранённого берём только правки адреса и модели
        val builtIns = Provider.PRESETS.map { p ->
            byId[p.id]?.let { s -> p.copy(baseUrl = s.baseUrl.ifBlank { p.baseUrl }, model = s.model.ifBlank { p.model }) } ?: p
        }
        return builtIns + byId.values.filter { !it.builtIn && Provider.PRESETS.none { p -> p.id == it.id } }
    }

    @Synchronized fun get(id: String) = all().find { it.id == id }

    @Synchronized fun save(p: Provider) {
        val list = all().filterNot { it.id == p.id } + p
        file.writeText(JSONArray(list.map { it.toJson() }).toString())
    }

    @Synchronized fun setModel(id: String, model: String) {
        val p = get(id) ?: throw IllegalArgumentException("нет такого сервиса")
        save(p.copy(model = model.trim().take(100)))
    }

    @Synchronized fun setBaseUrl(id: String, url: String) {
        val p = get(id) ?: throw IllegalArgumentException("нет такого сервиса")
        val u = url.trim().trimEnd('/')
        if (!u.startsWith("https://") && !u.startsWith("http://")) throw IllegalArgumentException("адрес должен начинаться с https://")
        save(p.copy(baseUrl = u))
    }

    @Synchronized fun delete(id: String) {
        if (Provider.PRESETS.any { it.id == id }) throw IllegalArgumentException("встроенный сервис удалить нельзя — просто не добавляйте ключ")
        file.writeText(JSONArray(all().filterNot { it.id == id }.map { it.toJson() }).toString())
    }
}
