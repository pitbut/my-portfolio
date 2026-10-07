package com.robutpit.pitbrowser

import java.net.URLEncoder

/**
 * Разбор ввода адресной строки: адрес или поисковый запрос.
 * Та же логика, что в desktop/src/omnibox.js — меняйте обе.
 */
object Omnibox {
    data class Engine(val name: String, val url: String)

    val ENGINES = linkedMapOf(
        "google" to Engine("Google", "https://www.google.com/search?q=%s"),
        "duckduckgo" to Engine("DuckDuckGo", "https://duckduckgo.com/?q=%s"),
        "bing" to Engine("Bing", "https://www.bing.com/search?q=%s"),
        "yandex" to Engine("Яндекс", "https://yandex.ru/search/?text=%s"),
    )

    private val SCHEME = Regex("^(https?|file|about|data|view-source|intent|content):", RegexOption.IGNORE_CASE)
    private val HOST_PORT = Regex("^[\\w.-]+:\\d{1,5}(/|$)")
    private val IPV4 = Regex("^\\d{1,3}(\\.\\d{1,3}){3}(:\\d+)?(/|$)")
    private val LOCALHOST = Regex("^localhost(:\\d+)?(/|$)", RegexOption.IGNORE_CASE)
    private val DOMAIN = Regex("^[^.\\s]+(\\.[^.\\s]+)*\\.\\p{L}{2,}[\\p{L}\\d-]*$")
    private val IPV6 = Regex("^\\[[\\da-fA-F:]+](:\\d+)?$")
    private val LOCAL = Regex("^(localhost|127\\.|10\\.|192\\.168\\.|\\[)", RegexOption.IGNORE_CASE)

    fun searchUrl(query: String, engine: String): String {
        val e = ENGINES[engine] ?: ENGINES.getValue("google")
        // encodeURIComponent-совместимо: пробел → %20
        return e.url.replace("%s", URLEncoder.encode(query, "UTF-8").replace("+", "%20"))
    }

    fun looksLikeHost(s: String): Boolean {
        if (s.any { it.isWhitespace() }) return false
        if (LOCALHOST.containsMatchIn(s) || IPV4.containsMatchIn(s) || HOST_PORT.containsMatchIn(s)) return true
        val host = s.split('/', '?', '#')[0]
        return DOMAIN.matches(host) || IPV6.matches(host)
    }

    fun toUrl(input: String?, engine: String = "google"): String? {
        val s = input?.trim().orEmpty()
        if (s.isEmpty()) return null
        if (s.startsWith("?")) return searchUrl(s.substring(1).trim(), engine)
        if (SCHEME.containsMatchIn(s) && s.none { it.isWhitespace() }) return s
        if (looksLikeHost(s)) return (if (LOCAL.containsMatchIn(s)) "http://" else "https://") + s
        return searchUrl(s, engine)
    }
}
