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

    /** Методы для страницы агентов. Ключ API наружу не отдаётся никогда — только маска. */
    private inner class Bridge {
        private val ctx get() = this@AgentsActivity

        private fun ok(v: Any? = true) = JSONObject().put("ok", true).put("value", v ?: JSONObject.NULL).toString()
        private fun err(e: Throwable) = JSONObject().put("ok", false).put("error", e.message ?: e.toString()).toString()
        private inline fun safe(f: () -> Any?): String = try { ok(f()) } catch (e: Exception) { err(e) }

        @JavascriptInterface
        fun state(): String = safe {
            val store = Agents.store(ctx)
            val key = KeyVault.load(ctx)
            JSONObject()
                .put("hasKey", key != null)
                .put("maskedKey", key?.let { KeyVault.masked(it) } ?: JSONObject.NULL)
                .put("agents", JSONArray(store.agents().map { a ->
                    a.toJson().put("lastRun", store.runs(a.id).firstOrNull()?.toJson() ?: JSONObject.NULL)
                }))
                .put("models", JSONArray(Agent.MODELS.map { (id, m) ->
                    JSONObject().put("id", id).put("title", m.title).put("inputPrice", m.inputPrice).put("outputPrice", m.outputPrice)
                }))
                .put("running", Agents.current?.toJson() ?: JSONObject.NULL)
                .put("todayTokens", Agents.todayTokens(ctx))
                .put("dailyLimit", Agents.dailyLimit(ctx))
                .put("canNotify", Agents.canNotify(ctx))
        }

        @JavascriptInterface
        fun setKey(key: String): String = safe {
            val k = key.trim()
            if (!k.startsWith("sk-ant-") || k.length < 20) throw IllegalArgumentException("ключ Claude API начинается с sk-ant-")
            KeyVault.save(ctx, k)
            Agents.checkKey(ctx, k) { e -> listener(JSONObject().put("type", "keyCheck").put("error", e ?: JSONObject.NULL)) }
            KeyVault.masked(k)
        }

        @JavascriptInterface
        fun clearKey(): String = safe { KeyVault.clear(ctx) }

        @JavascriptInterface
        fun saveAgent(json: String): String = safe {
            val o = JSONObject(json)
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
            if (agent.notify && Build.VERSION.SDK_INT >= 33 && !Agents.canNotify(ctx)) {
                runOnUiThread { requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 1) }
            }
            Agents.start(ctx, id)
        }

        @JavascriptInterface
        fun stop(): String = safe { Agents.stop() }

        @JavascriptInterface
        fun setDailyLimit(tokens: String): String = safe { Agents.setDailyLimit(ctx, tokens.toLong()); Agents.dailyLimit(ctx) }

        @JavascriptInterface
        fun openUrl(url: String): String = safe { runOnUiThread { openInBrowser(url) } }
    }

    companion object {
        const val PAGE = "file:///android_asset/agents.html"
    }
}
