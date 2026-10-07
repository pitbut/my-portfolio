package com.robutpit.pitbrowser.agents

import org.json.JSONArray
import org.json.JSONObject
import java.util.UUID
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit

/**
 * Команда агентов (у каждого может быть свой ИИ):
 *  chain    — цепочка: результат одного становится данными для следующего;
 *  manager  — первый участник руководит, остальные — помощники (инструмент ask_agent);
 *  discuss  — обсуждение по кругу N раундов, затем итог;
 *  compare  — «спросить всех»: все отвечают параллельно, судья (если выбран) сравнивает и пишет итог.
 */
data class Team(
    val id: String,
    val name: String,
    val mode: String,
    val members: List<String>,
    val task: String,
    val rounds: Int,
    val judge: String,
    val created: Long,
) {
    fun toJson(): JSONObject = JSONObject().put("id", id).put("name", name).put("mode", mode)
        .put("members", JSONArray(members)).put("task", task).put("rounds", rounds).put("judge", judge).put("created", created)

    companion object {
        val MODES = listOf("chain", "manager", "discuss", "compare")

        fun parse(o: JSONObject) = Team(
            o.getString("id"), o.optString("name"), o.optString("mode", "chain"),
            o.optJSONArray("members")?.let { a -> List(a.length()) { a.getString(it) } } ?: emptyList(),
            o.optString("task"), o.optInt("rounds", 2), o.optString("judge"), o.optLong("created"),
        )

        fun fromJson(o: JSONObject, existing: Team?, agentIds: Set<String>): Team {
            val name = o.optString("name").trim().take(60).ifEmpty { throw IllegalArgumentException("укажите название команды") }
            val mode = o.optString("mode").takeIf { it in MODES } ?: throw IllegalArgumentException("выберите режим команды")
            val members = (o.optJSONArray("members") ?: JSONArray()).let { a -> List(a.length()) { a.getString(it) } }
                .filter { it in agentIds }.distinct()
            val min = if (mode == "compare") 2 else 2
            if (members.size < min) throw IllegalArgumentException("в команде нужно минимум 2 агента")
            if (members.size > 6) throw IllegalArgumentException("в команде не больше 6 агентов")
            val task = o.optString("task").trim().take(8000)
            if (task.length < 5) throw IllegalArgumentException("опишите задачу команды")
            return Team(
                existing?.id ?: UUID.randomUUID().toString().take(8), name, mode, members, task,
                o.optInt("rounds", 2).coerceIn(1, 4), o.optString("judge").takeIf { it in agentIds } ?: "",
                existing?.created ?: System.currentTimeMillis(),
            )
        }
    }
}

/** Выполнение команды. engineFor — какой ИИ-движок у агента; context — обстановка запуска агента. */
class TeamRunner(
    private val engineFor: (Agent) -> Engine,
    private val contextFor: (onStep: (AgentRun) -> Unit, helpers: List<Agent>, askAgent: ((Agent, String) -> String)?) -> RunContext,
) {
    fun run(team: Team, agents: List<Agent>, onStep: (AgentRun) -> Unit): AgentRun {
        val run = AgentRun(team.id, System.currentTimeMillis(), model = "", provider = "team", title = team.name)
        val members = team.members.mapNotNull { id -> agents.find { it.id == id } }
        val judge = agents.find { it.id == team.judge }
        val ctx0 = contextFor({}, emptyList(), null)
        try {
            if (members.size < 2) throw IllegalStateException("в команде меньше двух агентов — кого-то удалили?")
            run.result = when (team.mode) {
                "chain" -> chain(team, members, run, onStep)
                "manager" -> manager(team, members, run, onStep)
                "discuss" -> discuss(team, members, judge, run, onStep)
                "compare" -> compare(team, members, judge, run, onStep)
                else -> throw IllegalStateException("неизвестный режим ${team.mode}")
            }
            run.status = if (ctx0.cancel.get()) "stopped" else "done"
        } catch (e: MemberFailed) {
            run.status = if (ctx0.cancel.get()) "stopped" else "error"
            run.error = e.message ?: "ошибка участника"
        } catch (e: Exception) {
            run.status = "error"
            run.error = e.message ?: e.toString()
        }
        run.finished = System.currentTimeMillis()
        onStep(run)
        return run
    }

    private class MemberFailed(message: String) : Exception(message)

    /** Запуск одного участника с учётом в общем отчёте команды. */
    private fun member(agent: Agent, task: String, team: AgentRun, onStep: (AgentRun) -> Unit,
                       helpers: List<Agent> = emptyList(), askAgent: ((Agent, String) -> String)? = null, label: String = agent.name): AgentRun {
        val entry = JSONObject().put("agentId", agent.id).put("name", label).put("provider", agent.provider)
            .put("model", agent.model).put("status", "running").put("result", "").put("error", "")
        synchronized(team) {
            team.members += entry
            team.steps += ToolExecutor.step("agent", "▶ $label")
        }
        onStep(team)
        val ctx = contextFor({ r ->
            synchronized(team) {
                entry.put("tokens", r.inputTokens + r.outputTokens).put("lastStep", r.steps.lastOrNull()?.optString("text") ?: "")
            }
            onStep(team)
        }, helpers, askAgent)
        if (ctx.cancel.get()) throw MemberFailed("остановлено")
        val r = engineFor(agent).run(agent, task, ctx)
        synchronized(team) {
            entry.put("status", r.status).put("result", r.result).put("error", r.error)
                .put("tokens", r.inputTokens + r.outputTokens).put("costUsd", r.costUsd()).put("costKnown", r.costKnown)
                .put("links", JSONArray(r.links)).put("steps", JSONArray(r.steps))
            team.inputTokens += r.inputTokens
            team.outputTokens += r.outputTokens
            team.webSearches += r.webSearches
            team.extraCostUsd += r.costUsd()
            if (!r.costKnown) team.costKnown = false
            team.links += r.links
            team.steps += ToolExecutor.step("agent", (if (r.status == "done") "✓ " else "✗ ") + label + if (r.status != "done") ": ${r.error.take(120)}" else "")
        }
        onStep(team)
        return r
    }

    private fun ok(r: AgentRun, name: String): String {
        if (r.status != "done") throw MemberFailed("«$name»: ${r.error.ifBlank { r.status }}")
        return r.result
    }

    private fun chain(team: Team, members: List<Agent>, run: AgentRun, onStep: (AgentRun) -> Unit): String {
        var prev = ""
        for ((i, a) in members.withIndex()) {
            val context = if (i == 0) "" else "Результат предыдущего агента «${members[i - 1].name}»:\n$prev"
            prev = ok(member(a, AgentPrompts.teamTask(a, team.task, context), run, onStep), a.name)
        }
        return prev
    }

    private fun manager(team: Team, members: List<Agent>, run: AgentRun, onStep: (AgentRun) -> Unit): String {
        val boss = members.first()
        val helpers = members.drop(1)
        val ask: (Agent, String) -> String = { helper, sub ->
            val r = member(helper, AgentPrompts.teamTask(helper, sub), run, onStep, label = "${helper.name} (помощник)")
            if (r.status == "done") r.result else "ошибка помощника: ${r.error}"
        }
        return ok(member(boss, AgentPrompts.teamTask(boss, team.task), run, onStep, helpers, ask, "${boss.name} (руководитель)"), boss.name)
    }

    private fun discuss(team: Team, members: List<Agent>, judge: Agent?, run: AgentRun, onStep: (AgentRun) -> Unit): String {
        val transcript = StringBuilder()
        for (round in 1..team.rounds) {
            for (a in members) {
                val prompt = if (transcript.isEmpty()) "Начни обсуждение: выскажи свою позицию по задаче."
                else "Раунд $round. Ответь участникам: согласись или возрази, дополни, исправь ошибки. Кратко."
                val context = if (transcript.isEmpty()) "" else "Обсуждение до тебя:\n$transcript"
                val r = ok(member(a, AgentPrompts.teamTask(a, "${team.task}\n\n$prompt", context), run, onStep, label = "${a.name} · раунд $round"), a.name)
                transcript.append("\n### ").append(a.name).append(" (раунд ").append(round).append(")\n").append(r).append('\n')
            }
        }
        val summarizer = judge ?: members.first()
        val r = member(summarizer, AgentPrompts.teamTask(summarizer,
            "${team.task}\n\nПодведи итог обсуждения: к чему пришли, где остались разногласия, итоговая рекомендация.", "Обсуждение:\n$transcript"),
            run, onStep, label = "${summarizer.name} · итог")
        return ok(r, summarizer.name) + "\n\n---\n## Ход обсуждения\n" + transcript
    }

    private fun compare(team: Team, members: List<Agent>, judge: Agent?, run: AgentRun, onStep: (AgentRun) -> Unit): String {
        val pool = Executors.newFixedThreadPool(members.size.coerceAtMost(MAX_PARALLEL))
        val futures = members.map { a -> pool.submit<AgentRun> { member(a, AgentPrompts.teamTask(a, team.task), run, onStep) } }
        val results = members.zip(futures.map { runCatching { it.get(15, TimeUnit.MINUTES) }.getOrNull() })
        pool.shutdownNow()
        val answers = results.joinToString("\n") { (a, r) ->
            "\n## ${a.name} (${a.provider}${if (a.model.isNotBlank()) ", ${a.model}" else ""})\n" +
                if (r?.status == "done") r.result else "_не ответил: ${r?.error ?: "время вышло"}_"
        }
        if (results.none { it.second?.status == "done" }) throw MemberFailed("ни один ИИ не ответил")
        if (judge == null) return "# Ответы разных ИИ\n$answers"
        val verdict = member(judge, AgentPrompts.teamTask(judge,
            "${team.task}\n\nСравни ответы разных ИИ: где они согласны, где расходятся, кто ошибся. Затем напиши лучший итоговый ответ.",
            "Ответы:\n$answers"), run, onStep, label = "${judge.name} · судья")
        return ok(verdict, judge.name) + "\n\n---\n# Ответы разных ИИ\n" + answers
    }

    companion object {
        const val MAX_PARALLEL = 4
    }
}
