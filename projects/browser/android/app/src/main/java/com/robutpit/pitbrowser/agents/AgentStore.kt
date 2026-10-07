package com.robutpit.pitbrowser.agents

import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.util.UUID

/** Агент: задача на естественном языке + модель + разрешённые инструменты. */
data class Agent(
    val id: String,
    val name: String,
    val task: String,
    val model: String,
    val effort: String,
    val web: Boolean,
    val notify: Boolean,
    val created: Long,
    /** ИИ-сервис (id из ProviderStore): claude, openai, gemini, grok, deepseek, qwen или свой. */
    val provider: String = Provider.CLAUDE,
) {
    fun toJson(): JSONObject = JSONObject()
        .put("id", id).put("name", name).put("task", task).put("model", model)
        .put("effort", effort).put("web", web).put("notify", notify).put("created", created).put("provider", provider)

    companion object {
        /** Модели, которые можно выбрать. Первая — по умолчанию. Цены — за 1 млн токенов, $ (на сентябрь 2026). */
        val MODELS = linkedMapOf(
            "claude-opus-5-5" to Model("Claude Opus 5.5 — самая умная", 4.0, 20.0),
            "claude-sonnet-5-5" to Model("Claude Sonnet 5.5 — быстрее и дешевле", 2.0, 10.0),
            "claude-haiku-4-5" to Model("Claude Haiku 4.5 — самая дешёвая", 1.0, 5.0),
        )
        val EFFORTS = listOf("low", "medium", "high")

        /** Проверка и нормализация того, что пришло из интерфейса. */
        fun fromJson(o: JSONObject, existing: Agent? = null): Agent {
            val name = o.optString("name").trim().take(60)
            val task = o.optString("task").trim().take(8000)
            if (name.isEmpty()) throw IllegalArgumentException("укажите название агента")
            if (task.length < 5) throw IllegalArgumentException("опишите задачу агента")
            val provider = o.optString("provider").ifBlank { Provider.CLAUDE }
            val model = if (provider == Provider.CLAUDE) {
                o.optString("model").takeIf { it.startsWith("claude-") } ?: MODELS.keys.first()
            } else {
                o.optString("model").trim().take(100) // проверит сам сервис; пусто — модель сервиса по умолчанию
            }
            val effort = o.optString("effort").takeIf { it in EFFORTS } ?: "medium"
            return Agent(
                id = existing?.id ?: UUID.randomUUID().toString().take(8),
                name = name, task = task, model = model, effort = effort,
                web = o.optBoolean("web", true), notify = o.optBoolean("notify", false),
                created = existing?.created ?: System.currentTimeMillis(),
                provider = provider,
            )
        }

        fun parse(o: JSONObject): Agent {
            val provider = o.optString("provider").ifBlank { Provider.CLAUDE }
            return Agent(
                o.getString("id"), o.optString("name"), o.optString("task"),
                if (provider == Provider.CLAUDE) o.optString("model").takeIf { it.startsWith("claude-") } ?: MODELS.keys.first() else o.optString("model"),
                o.optString("effort", "medium"), o.optBoolean("web", true), o.optBoolean("notify"), o.optLong("created"), provider,
            )
        }
    }

    data class Model(val title: String, val inputPrice: Double, val outputPrice: Double)
}

/** Результат одного запуска агента. */
data class AgentRun(
    val agentId: String,
    val started: Long,
    var finished: Long = 0,
    /** running | done | stopped | error | refused */
    var status: String = "running",
    val steps: MutableList<JSONObject> = mutableListOf(),
    var result: String = "",
    var error: String = "",
    val links: MutableList<JSONObject> = mutableListOf(),
    var inputTokens: Long = 0,
    var outputTokens: Long = 0,
    var webSearches: Long = 0,
    var model: String = "",
    var provider: String = Provider.CLAUDE,
    /** Стоимость частей, посчитанных отдельно (поиск через Claude, участники команды). */
    var extraCostUsd: Double = 0.0,
    /** false — есть запросы к ИИ, цены которого браузер не знает (показываем только токены). */
    var costKnown: Boolean = true,
    /** Для команд: результаты участников. */
    val members: MutableList<JSONObject> = mutableListOf(),
    /** Уникальный номер запуска (несколько агентов могут работать одновременно). */
    val runId: String = java.util.UUID.randomUUID().toString().take(8),
    var title: String = "",
) {
    /** Примерная стоимость по токенам (без отдельной платы за веб-поиск). */
    fun costUsd(): Double {
        val m = Agent.MODELS[model]
        val own = if (m != null && provider == Provider.CLAUDE) inputTokens / 1e6 * m.inputPrice + outputTokens / 1e6 * m.outputPrice else 0.0
        return own + extraCostUsd
    }

    fun toJson(): JSONObject = JSONObject()
        .put("agentId", agentId).put("started", started).put("finished", finished).put("status", status)
        .put("steps", JSONArray(steps)).put("result", result).put("error", error).put("links", JSONArray(links))
        .put("inputTokens", inputTokens).put("outputTokens", outputTokens).put("webSearches", webSearches)
        .put("model", model).put("costUsd", costUsd()).put("provider", provider).put("costKnown", costKnown)
        .put("extraCostUsd", extraCostUsd).put("members", JSONArray(members)).put("runId", runId).put("title", title)

    companion object {
        fun parse(o: JSONObject) = AgentRun(
            agentId = o.optString("agentId"), started = o.optLong("started"), finished = o.optLong("finished"),
            status = o.optString("status"),
            steps = o.optJSONArray("steps")?.let { a -> MutableList(a.length()) { a.getJSONObject(it) } } ?: mutableListOf(),
            result = o.optString("result"), error = o.optString("error"),
            links = o.optJSONArray("links")?.let { a -> MutableList(a.length()) { a.getJSONObject(it) } } ?: mutableListOf(),
            inputTokens = o.optLong("inputTokens"), outputTokens = o.optLong("outputTokens"),
            webSearches = o.optLong("webSearches"), model = o.optString("model"),
            provider = o.optString("provider").ifBlank { Provider.CLAUDE }, extraCostUsd = o.optDouble("extraCostUsd", 0.0),
            costKnown = o.optBoolean("costKnown", true),
            members = o.optJSONArray("members")?.let { a -> MutableList(a.length()) { a.getJSONObject(it) } } ?: mutableListOf(),
            runId = o.optString("runId").ifBlank { java.util.UUID.randomUUID().toString().take(8) }, title = o.optString("title"),
        )
    }
}

/** Агенты и история их запусков — JSON-файлы в папке приложения. */
class AgentStore(private val dir: File) {
    private val agentsFile = File(dir, "agents.json")

    init { dir.mkdirs() }

    @Synchronized fun agents(): List<Agent> {
        val arr = runCatching { JSONArray(agentsFile.readText()) }.getOrDefault(JSONArray())
        return List(arr.length()) { Agent.parse(arr.getJSONObject(it)) }
    }

    @Synchronized fun get(id: String) = agents().find { it.id == id }

    @Synchronized fun save(agent: Agent) {
        val list = agents().filterNot { it.id == agent.id } + agent
        write(agentsFile, JSONArray(list.sortedBy { it.created }.map { it.toJson() }).toString())
    }

    @Synchronized fun delete(id: String) {
        write(agentsFile, JSONArray(agents().filterNot { it.id == id }.map { it.toJson() }).toString())
        runsFile(id).delete()
        teams().filter { id in it.members || it.judge == id }.forEach { t ->
            saveTeam(t.copy(members = t.members - id, judge = if (t.judge == id) "" else t.judge))
        }
    }

    @Synchronized fun runs(agentId: String): List<AgentRun> {
        val arr = runCatching { JSONArray(runsFile(agentId).readText()) }.getOrDefault(JSONArray())
        return List(arr.length()) { AgentRun.parse(arr.getJSONObject(it)) }
    }

    @Synchronized fun addRun(run: AgentRun) {
        val list = (listOf(run) + runs(run.agentId)).take(MAX_RUNS)
        write(runsFile(run.agentId), JSONArray(list.map { it.toJson() }).toString())
    }

    /** Сколько токенов потрачено за сегодня всеми агентами и командами (для лимита в день). */
    @Synchronized fun tokensSince(since: Long): Long =
        (agents().map { it.id } + teams().map { it.id }).sumOf { id -> runs(id).filter { it.started >= since }.sumOf { it.inputTokens + it.outputTokens } }

    // ------------------------------------------------------------ команды

    private val teamsFile = File(dir, "teams.json")

    @Synchronized fun teams(): List<Team> {
        val arr = runCatching { JSONArray(teamsFile.readText()) }.getOrDefault(JSONArray())
        return List(arr.length()) { Team.parse(arr.getJSONObject(it)) }
    }

    @Synchronized fun team(id: String) = teams().find { it.id == id }

    @Synchronized fun saveTeam(t: Team) {
        write(teamsFile, JSONArray((teams().filterNot { it.id == t.id } + t).sortedBy { it.created }.map { it.toJson() }).toString())
    }

    @Synchronized fun deleteTeam(id: String) {
        write(teamsFile, JSONArray(teams().filterNot { it.id == id }.map { it.toJson() }).toString())
        runsFile(id).delete()
    }

    private fun runsFile(id: String) = File(dir, "runs-${id.filter { it.isLetterOrDigit() }}.json")

    private fun write(f: File, text: String) {
        val tmp = File(f.path + ".tmp")
        tmp.writeText(text)
        tmp.renameTo(f)
    }

    companion object {
        const val MAX_RUNS = 20
    }
}
