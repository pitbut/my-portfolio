package com.robutpit.pitbrowser

import android.Manifest
import android.annotation.SuppressLint
import android.app.Activity
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.webkit.JavascriptInterface
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import com.robutpit.pitbrowser.agents.Agent
import com.robutpit.pitbrowser.agents.Agents
import com.robutpit.pitbrowser.agents.KeyVault
import com.robutpit.pitbrowser.agents.Provider
import com.robutpit.pitbrowser.agents.Team
import org.json.JSONArray
import org.json.JSONObject

/**
 * Раздел «Агенты». Интерфейс — встроенная страница assets/agents.html; мост AgentsNative есть только
 * в этом окне, а окно открывает только свою страницу (любые ссылки уходят в обычную вкладку браузера).
 */
class AgentsActivity : Activity() {
    private lateinit var web: WebView
    private val listener: (JSONObject) -> Unit = { e -> runOnUiThread { push(e) } }

    @SuppressLint("SetJavaScriptEnabled", "AddJavascriptInterface")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        web = WebView(this)
        web.settings.javaScriptEnabled = true
        web.settings.domStorageEnabled = true
        web.settings.allowFileAccess = false
        web.settings.allowContentAccess = false
        web.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
                openInBrowser(request.url.toString())
                return true
            }
        }
        web.addJavascriptInterface(Bridge(), "AgentsNative")
        setContentView(web)
        applyInsets()
        web.loadUrl(PAGE)
        Agents.listen(listener)
    }

    override fun onResume() { super.onResume(); Agents.screenVisible = true }
    override fun onPause() { Agents.screenVisible = false; super.onPause() }

    override fun onDestroy() {
        Agents.unlisten(listener)
        web.destroy()
        super.onDestroy()
    }

    @Deprecated("Deprecated in Java")
    override fun onBackPressed() {
        web.evaluateJavascript("window.onBack && window.onBack()") { handled ->
            @Suppress("DEPRECATION")
            if (handled != "true") super.onBackPressed()
        }
    }

    private fun push(e: JSONObject) {
        if (web.url?.startsWith(PAGE) == true) web.evaluateJavascript("window.onAgentEvent && window.onAgentEvent(${JSONObject.quote(e.toString())})", null)
    }

    private fun openInBrowser(url: String) {
        if (!url.startsWith("https://") && !url.startsWith("http://")) return
        startActivity(Intent(this, MainActivity::class.java).setAction(Intent.ACTION_VIEW).setData(Uri.parse(url)))
    }

    private fun applyInsets() {
        web.setOnApplyWindowInsetsListener { v, insets ->
            if (Build.VERSION.SDK_INT >= 30) {
                val b = insets.getInsets(android.view.WindowInsets.Type.systemBars() or android.view.WindowInsets.Type.ime())
                v.setPadding(b.left, b.top, b.right, b.bottom)
            } else {
                @Suppress("DEPRECATION")
                v.setPadding(insets.systemWindowInsetLeft, insets.systemWindowInsetTop, insets.systemWindowInsetRight, insets.systemWindowInsetBottom)
            }
            insets
        }
    }

    /** Методы для страницы агентов. Ключи API наружу не отдаются никогда — только маски. */
    private inner class Bridge {
        private val ctx get() = this@AgentsActivity

        private fun ok(v: Any? = true) = JSONObject().put("ok", true).put("value", v ?: JSONObject.NULL).toString()
        private fun err(e: Throwable) = JSONObject().put("ok", false).put("error", e.message ?: e.toString()).toString()
        private inline fun safe(f: () -> Any?): String = try { ok(f()) } catch (e: Exception) { err(e) }

        private fun providerJson(p: Provider) = p.toJson()
            .put("hasKey", Agents.hasKey(ctx, p))
            .put("maskedKey", KeyVault.load(ctx, p.id)?.let { KeyVault.masked(it) } ?: JSONObject.NULL)

        @JavascriptInterface
        fun state(): String = safe {
            val store = Agents.store(ctx)
            JSONObject()
                .put("providers", JSONArray(Agents.providers(ctx).all().map { providerJson(it) }))
                .put("agents", JSONArray(store.agents().map { a ->
                    a.toJson().put("lastRun", store.runs(a.id).firstOrNull()?.toJson() ?: JSONObject.NULL)
                }))
                .put("teams", JSONArray(store.teams().map { t ->
                    t.toJson().put("lastRun", store.runs(t.id).firstOrNull()?.toJson() ?: JSONObject.NULL)
                }))
                .put("claudePrices", JSONObject().apply {
                    Agent.MODELS.forEach { (id, m) -> put(id, JSONObject().put("title", m.title).put("in", m.inputPrice).put("out", m.outputPrice)) }
                })
                .put("running", JSONArray(Agents.runningRuns().map { it.toJson() }))
                .put("maxParallel", Agents.MAX_PARALLEL)
                .put("todayTokens", Agents.todayTokens(ctx))
                .put("dailyLimit", Agents.dailyLimit(ctx))
                .put("canNotify", Agents.canNotify(ctx))
        }

        // ---------------- ИИ-сервисы и ключи

        @JavascriptInterface
        fun setProviderKey(providerId: String, key: String): String = safe {
            val p = Agents.providers(ctx).get(providerId) ?: throw IllegalArgumentException("нет такого сервиса")
            val k = key.trim()
            if (p.kind == "anthropic" && (!k.startsWith("sk-ant-") || k.length < 20)) throw IllegalArgumentException("ключ Claude API начинается с sk-ant-")
            if (k.length < 8 || k.any { it.isWhitespace() }) throw IllegalArgumentException("похоже, ключ скопирован не полностью")
            KeyVault.save(ctx, k, p.id)
            loadModels(p.id)
            KeyVault.masked(k)
        }

        @JavascriptInterface
        fun clearProviderKey(providerId: String): String = safe { KeyVault.clear(ctx, providerId) }

        /** Проверить ключ и получить модели сервиса — ответ придёт событием "models". */
        @JavascriptInterface
        fun loadModels(providerId: String): String = safe {
            Agents.checkKey(ctx, providerId) { models, error ->
                listener(JSONObject().put("type", "models").put("provider", providerId)
                    .put("models", models?.let { JSONArray(it) } ?: JSONObject.NULL).put("error", error ?: JSONObject.NULL))
            }
        }

        @JavascriptInterface
        fun setProviderModel(providerId: String, model: String): String = safe { Agents.providers(ctx).setModel(providerId, model) }

        @JavascriptInterface
        fun setProviderUrl(providerId: String, url: String): String = safe { Agents.providers(ctx).setBaseUrl(providerId, url) }

        @JavascriptInterface
        fun addProvider(json: String): String = safe {
            val o = JSONObject(json)
            val p = Provider.custom(o)
            if (Agents.providers(ctx).get(p.id)?.builtIn == true) throw IllegalArgumentException("такое имя занято встроенным сервисом")
            Agents.providers(ctx).save(p)
            o.optString("key").trim().takeIf { it.isNotEmpty() }?.let { KeyVault.save(ctx, it, p.id) }
            providerJson(p)
        }

        @JavascriptInterface
        fun deleteProvider(providerId: String): String = safe { Agents.providers(ctx).delete(providerId); KeyVault.clear(ctx, providerId) }

        // ---------------- агенты

        @JavascriptInterface
        fun saveAgent(json: String): String = safe {
            val o = JSONObject(json)
            if (Agents.providers(ctx).get(o.optString("provider").ifBlank { Provider.CLAUDE }) == null) throw IllegalArgumentException("выберите ИИ")
            val existing = o.optString("id").takeIf { it.isNotEmpty() }?.let { Agents.store(ctx).get(it) }
            val a = Agent.fromJson(o, existing)
            Agents.store(ctx).save(a)
            a.toJson()
        }

        @JavascriptInterface
        fun deleteAgent(id: String): String = safe { Agents.store(ctx).delete(id) }

        @JavascriptInterface
        fun runs(id: String): String = safe { JSONArray(Agents.store(ctx).runs(id).map { it.toJson() }) }

        @JavascriptInterface
        fun run(id: String): String = safe {
            val agent = Agents.store(ctx).get(id) ?: throw IllegalStateException("агент не найден")
            askNotifications(agent.notify)
            Agents.start(ctx, id)
        }

        // ---------------- команды

        @JavascriptInterface
        fun saveTeam(json: String): String = safe {
            val o = JSONObject(json)
            val store = Agents.store(ctx)
            val existing = o.optString("id").takeIf { it.isNotEmpty() }?.let { store.team(it) }
            val t = Team.fromJson(o, existing, store.agents().map { it.id }.toSet())
            store.saveTeam(t)
            t.toJson()
        }

        @JavascriptInterface
        fun deleteTeam(id: String): String = safe { Agents.store(ctx).deleteTeam(id) }

        @JavascriptInterface
        fun runTeam(id: String): String = safe {
            val store = Agents.store(ctx)
            val t = store.team(id) ?: throw IllegalStateException("команда не найдена")
            askNotifications(store.agents().any { it.id in t.members && it.notify })
            Agents.startTeam(ctx, id)
        }

        // ---------------- общее

        @JavascriptInterface
        fun stop(runId: String): String = safe { Agents.stop(runId) }

        @JavascriptInterface
        fun stopAll(): String = safe { Agents.stopAll() }

        @JavascriptInterface
        fun setDailyLimit(tokens: String): String = safe { Agents.setDailyLimit(ctx, tokens.toLong()); Agents.dailyLimit(ctx) }

        @JavascriptInterface
        fun openUrl(url: String): String = safe { runOnUiThread { openInBrowser(url) } }

        private fun askNotifications(need: Boolean) {
            if (need && Build.VERSION.SDK_INT >= 33 && !Agents.canNotify(ctx)) {
                runOnUiThread { requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 1) }
            }
        }
    }

    companion object {
        const val PAGE = "file:///android_asset/agents.html"
    }
}
