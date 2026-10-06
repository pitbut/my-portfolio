package com.robutpit.pitbrowser.apps

import org.json.JSONArray
import org.json.JSONObject
import java.io.File

/**
 * Данные браузера о приложении (не доступны самому приложению напрямую):
 * решения пользователя по разрешениям и таблица рекордов. Файл state/<id>.json.
 */
class AppState(private val dir: File, val manifest: AppManifest) {

    data class Score(val score: Double, val player: String, val time: Long, val level: String?)

    data class SubmitResult(val best: Score?, val rank: Int, val isRecord: Boolean)

    private val file = File(dir, "${manifest.id}.json")
    private var data: JSONObject = runCatching { JSONObject(file.readText()) }.getOrDefault(JSONObject())

    // ------------------------------------------------------------ разрешения

    /** true/false — пользователь решил, null — ещё не спрашивали. */
    fun permission(name: String): Boolean? {
        val p = data.optJSONObject("permissions") ?: return null
        return if (p.has(name)) p.optBoolean(name) else null
    }

    fun setPermission(name: String, granted: Boolean) {
        val p = data.optJSONObject("permissions") ?: JSONObject().also { data.put("permissions", it) }
        p.put(name, granted)
        save()
    }

    fun clearPermission(name: String) {
        data.optJSONObject("permissions")?.remove(name)
        save()
    }

    /** Разрешено ли сейчас: объявлено в манифесте и (для опасных) одобрено пользователем. */
    fun allowed(name: String): Boolean = manifest.has(name) && (name !in AppManifest.RUNTIME || permission(name) == true)

    // ------------------------------------------------------------ Bluetooth-устройства

    /** Устройство, которое пользователь сам выбрал для этого приложения. */
    data class Device(val id: String, val name: String, val type: String)

    /** Приложение видит только устройства, выбранные пользователем в окне выбора. */
    fun devices(): List<Device> {
        val arr = data.optJSONArray("devices") ?: return emptyList()
        return List(arr.length()) { i -> arr.getJSONObject(i).let { Device(it.getString("id"), it.optString("name"), it.optString("type")) } }
    }

    fun isApproved(id: String, type: String) = devices().any { it.id.equals(id, ignoreCase = true) && it.type == type }

    fun approveDevice(d: Device) {
        val list = devices().filterNot { it.id.equals(d.id, ignoreCase = true) && it.type == d.type } + d
        val arr = JSONArray()
        list.takeLast(MAX_DEVICES).forEach { arr.put(JSONObject().put("id", it.id).put("name", it.name).put("type", it.type)) }
        data.put("devices", arr)
        save()
    }

    fun forgetDevices() { data.remove("devices"); save() }

    // ------------------------------------------------------------ рекорды

    fun scores(): List<Score> {
        val arr = data.optJSONArray("scores") ?: return emptyList()
        return List(arr.length()) { i ->
            val o = arr.getJSONObject(i)
            Score(o.getDouble("score"), o.optString("player"), o.optLong("time"), o.optString("level").ifEmpty { null })
        }
    }

    fun top(limit: Int = 10, level: String? = null): List<Score> =
        scores().filter { level == null || it.level == level }.take(limit.coerceIn(1, MAX_SCORES))

    fun best(level: String? = null): Score? = top(1, level).firstOrNull()

    fun submit(score: Double, player: String, level: String? = null, now: Long = System.currentTimeMillis()): SubmitResult {
        require(score.isFinite()) { "score должен быть числом" }
        val prevBest = best(level)
        val entry = Score(score, player.take(30), now, level?.take(40))
        val all = (scores() + entry).sortedWith(comparator()).take(MAX_SCORES)
        val arr = JSONArray()
        all.forEach { s ->
            arr.put(JSONObject().put("score", s.score).put("player", s.player).put("time", s.time).apply { s.level?.let { put("level", it) } })
        }
        data.put("scores", arr)
        save()
        val sameLevel = all.filter { level == null || it.level == level }
        val rank = sameLevel.indexOf(entry).let { if (it < 0) 0 else it + 1 } // 0 — не попал в таблицу
        val isRecord = prevBest == null || comparator().compare(entry, prevBest) < 0
        return SubmitResult(best(level), rank, isRecord)
    }

    fun clearScores() { data.remove("scores"); save() }

    fun delete() { file.delete() }

    private fun comparator(): Comparator<Score> {
        val byScore = if (manifest.scoreOrder == "asc") compareBy<Score> { it.score } else compareByDescending { it.score }
        return byScore.thenBy { it.time } // при равенстве выше тот, кто набрал раньше
    }

    private fun save() {
        dir.mkdirs()
        val tmp = File(dir, "${manifest.id}.json.tmp")
        tmp.writeText(data.toString())
        tmp.renameTo(file)
    }

    companion object {
        const val MAX_SCORES = 100
        const val MAX_DEVICES = 20
    }
}
