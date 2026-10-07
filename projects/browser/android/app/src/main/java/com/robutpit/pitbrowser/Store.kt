package com.robutpit.pitbrowser

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

/** Закладки, история, открытые вкладки и настройки — в SharedPreferences. */
class Store(context: Context) {
    data class Entry(val url: String, val title: String, val time: Long = System.currentTimeMillis())

    private val prefs = context.getSharedPreferences("pitbrowser", Context.MODE_PRIVATE)

    var searchEngine: String
        get() = prefs.getString("engine", "google") ?: "google"
        set(v) = prefs.edit().putString("engine", v).apply()

    var desktopMode: Boolean
        get() = prefs.getBoolean("desktop", false)
        set(v) = prefs.edit().putBoolean("desktop", v).apply()

    // --- закладки
    fun bookmarks(): List<Entry> = read("bookmarks")
    fun isBookmarked(url: String) = bookmarks().any { it.url == url }
    fun toggleBookmark(url: String, title: String): Boolean {
        val list = bookmarks().toMutableList()
        val removed = list.removeAll { it.url == url }
        if (!removed) list.add(Entry(url, title.ifBlank { url }))
        write("bookmarks", list)
        return !removed
    }
    fun removeBookmark(url: String) = write("bookmarks", bookmarks().filter { it.url != url })

    // --- история
    fun history(): List<Entry> = read("history")
    fun addHistory(url: String, title: String) {
        val list = history().toMutableList()
        if (list.firstOrNull()?.url == url) list.removeAt(0)
        list.add(0, Entry(url, title.ifBlank { url }))
        write("history", list.take(HISTORY_LIMIT))
    }
    fun updateHistoryTitle(url: String, title: String) {
        val list = history().toMutableList()
        val first = list.firstOrNull() ?: return
        if (first.url == url && title.isNotBlank() && first.title != title) {
            list[0] = first.copy(title = title)
            write("history", list)
        }
    }
    fun removeHistory(url: String) = write("history", history().filter { it.url != url })
    fun clearHistory() = write("history", emptyList())

    // --- открытые вкладки (восстанавливаются при запуске)
    fun saveTabs(urls: List<String>, active: Int) {
        prefs.edit().putString("tabs", JSONArray(urls).toString()).putInt("activeTab", active).apply()
    }
    fun savedTabs(): Pair<List<String>, Int> {
        val arr = runCatching { JSONArray(prefs.getString("tabs", "[]")) }.getOrDefault(JSONArray())
        return List(arr.length()) { arr.getString(it) } to prefs.getInt("activeTab", 0)
    }

    /** Подсказки адресной строки: закладки, затем история. */
    fun suggest(q: String): List<Entry> {
        val s = q.trim().lowercase()
        if (s.isEmpty()) return emptyList()
        val seen = HashSet<String>()
        return (bookmarks() + history())
            .filter { (it.url.lowercase().contains(s) || it.title.lowercase().contains(s)) && seen.add(it.url) }
            .take(6)
    }

    private fun read(key: String): List<Entry> {
        val arr = runCatching { JSONArray(prefs.getString(key, "[]")) }.getOrDefault(JSONArray())
        return List(arr.length()) {
            val o = arr.getJSONObject(it)
            Entry(o.getString("url"), o.optString("title"), o.optLong("time"))
        }
    }

    private fun write(key: String, list: List<Entry>) {
        val arr = JSONArray()
        list.forEach { arr.put(JSONObject().put("url", it.url).put("title", it.title).put("time", it.time)) }
        prefs.edit().putString(key, arr.toString()).apply()
    }

    companion object {
        const val HISTORY_LIMIT = 1000
    }
}
