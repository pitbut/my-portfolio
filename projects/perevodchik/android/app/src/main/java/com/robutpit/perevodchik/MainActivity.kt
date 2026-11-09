package com.robutpit.perevodchik

import android.Manifest
import android.annotation.SuppressLint
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Color
import android.os.Build
import android.os.Bundle
import android.view.View
import android.view.WindowInsets
import android.view.WindowManager
import android.webkit.PermissionRequest
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.webkit.WebViewAssetLoader

/**
 * Одно окно с WebView. Интерфейс — тот же index.html, что и на сайте (лежит в assets/www).
 * Распознавание и синтез речи — родные Android (SpeechBridge), т.к. в WebView Web Speech API не работает.
 */
class MainActivity : Activity() {

    private lateinit var web: WebView
    private lateinit var bridge: SpeechBridge
    private var pendingWebPermission: PermissionRequest? = null

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        web = WebView(this)
        web.setBackgroundColor(Color.parseColor("#0F172A"))
        setContentView(web)
        applyInsets()

        // Отдаём файлы из assets по https-адресу: так работают localStorage, fetch и микрофон
        val loader = WebViewAssetLoader.Builder()
            .addPathHandler("/assets/", WebViewAssetLoader.AssetsPathHandler(this))
            .build()

        web.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            mediaPlaybackRequiresUserGesture = false
            allowFileAccess = false
            allowContentAccess = false
            textZoom = 100
        }

        web.webViewClient = object : WebViewClient() {
            // Если процесс WebView упал — перезапускаем экран, а не всё приложение
            override fun onRenderProcessGone(view: WebView, detail: android.webkit.RenderProcessGoneDetail): Boolean {
                recreate(); return true
            }

            override fun shouldInterceptRequest(view: WebView, request: WebResourceRequest): WebResourceResponse? =
                loader.shouldInterceptRequest(request.url)

            // Внутри приложения открываем только свой интерфейс, внешние ссылки — в браузере
            override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
                if (request.url.host == "appassets.androidplatform.net") return false
                try { startActivity(Intent(Intent.ACTION_VIEW, request.url)) } catch (_: Exception) {}
                return true
            }
        }

        // Режим Whisper использует микрофон через getUserMedia
        web.webChromeClient = object : WebChromeClient() {
            override fun onPermissionRequest(request: PermissionRequest) {
                runOnUiThread {
                    if (PermissionRequest.RESOURCE_AUDIO_CAPTURE !in request.resources) {
                        request.deny(); return@runOnUiThread
                    }
                    if (hasMic()) {
                        request.grant(arrayOf(PermissionRequest.RESOURCE_AUDIO_CAPTURE))
                    } else {
                        pendingWebPermission = request
                        requestPermissions(arrayOf(Manifest.permission.RECORD_AUDIO), REQ_MIC)
                    }
                }
            }
        }

        bridge = SpeechBridge(this, web)
        web.addJavascriptInterface(bridge, "AndroidBridge")

        if (savedInstanceState != null) web.restoreState(savedInstanceState)
        else web.loadUrl("https://appassets.androidplatform.net/assets/www/index.html")
    }

    /** Android 15 рисует приложение под системными панелями — отодвигаем контент */
    private fun applyInsets() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            window.setDecorFitsSystemWindows(false)
            web.setOnApplyWindowInsetsListener { v: View, insets: WindowInsets ->
                val bars = insets.getInsets(WindowInsets.Type.systemBars() or WindowInsets.Type.ime() or WindowInsets.Type.displayCutout())
                v.setPadding(bars.left, bars.top, bars.right, bars.bottom)
                WindowInsets.CONSUMED
            }
            window.decorView.setBackgroundColor(Color.parseColor("#1E293B"))
        }
    }

    fun hasMic() = checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED

    fun requestMic() = runOnUiThread {
        requestPermissions(arrayOf(Manifest.permission.RECORD_AUDIO), REQ_MIC)
    }

    @Deprecated("Deprecated in Java")
    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode != REQ_MIC) return
        val granted = grantResults.isNotEmpty() && grantResults[0] == PackageManager.PERMISSION_GRANTED
        pendingWebPermission?.let {
            if (granted) it.grant(arrayOf(PermissionRequest.RESOURCE_AUDIO_CAPTURE)) else it.deny()
            pendingWebPermission = null
        }
        bridge.js("window.onMicPermission && window.onMicPermission($granted)")
    }

    fun keepScreenOn(on: Boolean) = runOnUiThread {
        if (on) window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        else window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
    }

    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        web.saveState(outState)
    }

    /** «Назад» сначала закрывает настройки/полноэкранный показ, потом выходит */
    @Deprecated("Deprecated in Java")
    override fun onBackPressed() {
        web.evaluateJavascript("window.appBack ? appBack() : false") { handled ->
            if (handled != "true") {
                @Suppress("DEPRECATION")
                super.onBackPressed()
            }
        }
    }

    override fun onResume() {
        super.onResume()
        // Вернулись в приложение — продолжаем слушать, если слушали до ухода
        bridge.js("window.onAppResume && window.onAppResume()")
    }

    override fun onPause() {
        super.onPause()
        // В фоне микрофон не держим
        bridge.js("window.onAppPause && window.onAppPause()")
    }

    override fun onDestroy() {
        bridge.release()
        web.destroy()
        super.onDestroy()
    }

    companion object { private const val REQ_MIC = 1 }
}
