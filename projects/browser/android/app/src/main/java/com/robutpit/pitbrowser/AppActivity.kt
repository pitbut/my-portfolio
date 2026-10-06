package com.robutpit.pitbrowser

import android.Manifest
import android.annotation.SuppressLint
import android.app.Activity
import android.app.ActivityManager
import android.app.AlertDialog
import android.content.Intent
import android.content.pm.ActivityInfo
import android.content.pm.PackageManager
import android.graphics.Color
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.view.KeyEvent
import android.view.View
import android.view.WindowInsets
import android.view.WindowInsetsController
import android.view.WindowManager
import android.webkit.GeolocationPermissions
import android.webkit.PermissionRequest
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.EditText
import android.widget.FrameLayout
import android.widget.Toast
import androidx.webkit.JavaScriptReplyProxy
import androidx.webkit.WebViewCompat
import androidx.webkit.WebViewFeature
import com.robutpit.pitbrowser.apps.AppManifest
import com.robutpit.pitbrowser.apps.AppServer
import com.robutpit.pitbrowser.apps.AudioBridge
import com.robutpit.pitbrowser.apps.AppState
import com.robutpit.pitbrowser.apps.Apps
import com.robutpit.pitbrowser.apps.BleUuids
import com.robutpit.pitbrowser.apps.BluetoothBridge
import com.robutpit.pitbrowser.apps.DeviceSensors
import org.json.JSONArray
import org.json.JSONObject

/**
 * Установленное приложение на весь экран. Только здесь странице доступен PitSDK (window.pitNative),
 * и только для адреса самого приложения.
 */
class AppActivity : Activity() {

    private lateinit var manifest: AppManifest
    private lateinit var state: AppState
    private lateinit var server: AppServer
    private lateinit var web: WebView
    private lateinit var sensors: DeviceSensors
    private lateinit var bt: BluetoothBridge
    private lateinit var audio: AudioBridge
    private var pendingBtEnable: ((Boolean) -> Unit)? = null

    private var proxy: JavaScriptReplyProxy? = null
    private var captureBack = false
    private var lastBack = 0L
    private var backPresses = 0
    private var pendingAndroid: ((Boolean) -> Unit)? = null
    private var fullscreenView: View? = null
    private var fullscreenCallback: WebChromeClient.CustomViewCallback? = null

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val id = intent.data?.host
        val m = id?.let { Apps.packages(this).get(it) }
        if (m == null) {
            Toast.makeText(this, "Приложение не установлено", Toast.LENGTH_LONG).show()
            finish(); return
        }
        if (!WebViewFeature.isFeatureSupported(WebViewFeature.WEB_MESSAGE_LISTENER)) {
            AlertDialog.Builder(this)
                .setMessage("Для приложений нужна более новая версия Android System WebView. Обновите её в Google Play.")
                .setPositiveButton("ОК") { _, _ -> finish() }
                .setOnCancelListener { finish() }
                .show()
            return
        }
        manifest = m
        state = Apps.state(this, m)
        server = AppServer(this, m)
        sensors = DeviceSensors(this) { type, values, ts -> sendEvent("sensor:$type", sensorEvent(type, values, ts)) }
        bt = BluetoothBridge(this, state) { event, data -> sendEvent(event, data) }
        audio = AudioBridge(this) { event, data -> sendEvent(event, data) }
        if (m.has("headphones")) audio.start()

        requestedOrientation = orientationOf(m.orientation)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            window.attributes.layoutInDisplayCutoutMode = WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_SHORT_EDGES
        }
        setRecentsCard()

        web = WebView(this)
        web.setBackgroundColor(Color.BLACK)
        with(web.settings) {
            javaScriptEnabled = true
            domStorageEnabled = true
            mediaPlaybackRequiresUserGesture = false // звук в играх без лишнего нажатия
            allowFileAccess = false
            allowContentAccess = false
            setSupportZoom(false)
            useWideViewPort = true
            loadWithOverviewMode = true
            setGeolocationEnabled(m.has("geolocation"))
            cacheMode = if (m.has("network")) WebSettings.LOAD_DEFAULT else WebSettings.LOAD_CACHE_ELSE_NETWORK
        }
        WebViewCompat.addWebMessageListener(web, "pitNative", setOf(m.origin)) { _, message, sourceOrigin, isMainFrame, reply ->
            if (!isMainFrame || sourceOrigin.toString().trimEnd('/') != m.origin) return@addWebMessageListener
            proxy = reply
            handle(message.data ?: return@addWebMessageListener)
        }
        web.webViewClient = Client()
        web.webChromeClient = Chrome()
        setContentView(FrameLayout(this).apply { setBackgroundColor(Color.BLACK); addView(web) })
        hideSystemBars()
        web.loadUrl(m.entryUrl)
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        // повторный запуск того же приложения — просто показываем его
    }

    override fun onResume() {
        super.onResume()
        if (!::web.isInitialized) return
        web.onResume()
        sensors.resume()
        audio.resume()
        hideSystemBars()
        sendEvent("resume", null)
    }

    override fun onPause() {
        if (::web.isInitialized) {
            sendEvent("pause", null)
            sensors.pause()
            audio.pause()
            web.onPause()
        }
        super.onPause()
    }

    override fun onDestroy() {
        if (::web.isInitialized) {
            sensors.stopAll()
            bt.closeAll()
            audio.release()
            web.destroy()
        }
        super.onDestroy()
    }

    override fun onWindowFocusChanged(hasFocus: Boolean) {
        super.onWindowFocusChanged(hasFocus)
        if (hasFocus && ::web.isInitialized) hideSystemBars()
    }

    /** Кнопки гарнитуры и громкости — приложению, если оно их запросило. */
    override fun dispatchKeyEvent(event: KeyEvent): Boolean {
        if (::audio.isInitialized && audio.onKey(event)) return true
        return super.dispatchKeyEvent(event)
    }

    @Deprecated("Deprecated in Java")
    override fun onBackPressed() {
        val now = System.currentTimeMillis()
        // страховка: если игра зависла и не отвечает на «Назад», три быстрых нажатия закрывают её
        backPresses = if (now - lastBack < 600) backPresses + 1 else 1
        lastBack = now
        when {
            !::web.isInitialized || backPresses >= 3 -> finishAndRemoveTask()
            fullscreenView != null -> fullscreenCallback?.onCustomViewHidden()
            captureBack -> sendEvent("back", null)
            web.canGoBack() -> web.goBack()
            else -> finishAndRemoveTask()
        }
    }

    // ------------------------------------------------------------------ PitSDK

    private fun handle(raw: String) {
        val msg = runCatching { JSONObject(raw) }.getOrNull() ?: return
        val id = msg.optInt("id")
        val p = msg.optJSONObject("params") ?: JSONObject()
        val ok = { result: Any? -> reply(id, result, null) }
        val fail = { error: String -> reply(id, null, error) }
        try {
            when (msg.optString("method")) {
                "hello" -> ok(appInfo())
                "app.exit" -> { ok(true); finishAndRemoveTask() }
                "app.captureBack" -> { captureBack = p.optBoolean("enabled", true); ok(true) }

                "permissions.query" -> ok(permissionStatus(p.optString("name")))
                "permissions.request" -> {
                    val names = p.optJSONArray("names") ?: JSONArray()
                    requestPermissions(List(names.length()) { names.optString(it) }) { result ->
                        ok(JSONObject().apply { result.forEach { (k, v) -> put(k, v) } })
                    }
                }

                "sensors.list" -> { require("sensors"); ok(JSONArray(sensors.available())) }
                "sensors.start" -> {
                    require("sensors")
                    val type = p.optString("type")
                    if (!sensors.start(type, p.optInt("hz", 60))) fail("датчик «$type» недоступен на этом телефоне") else ok(true)
                }
                "sensors.stop" -> { sensors.stop(p.optString("type")); ok(true) }

                "vibrate" -> {
                    require("vibrate")
                    val arr = p.optJSONArray("pattern") ?: JSONArray().put(50)
                    sensors.vibrate(LongArray(minOf(arr.length(), 40)) { arr.optLong(it).coerceIn(0, 5000) })
                    ok(true)
                }

                "screen.keepOn" -> {
                    require("screen")
                    if (p.optBoolean("on", true)) window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
                    else window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
                    ok(true)
                }
                "bluetooth.status" -> { require("bluetooth"); ok(bt.status()) }
                "bluetooth.getDevices" -> { require("bluetooth"); ok(bt.approvedDevices()) }
                "bluetooth.enable" -> withBluetooth(fail) { ok(true) }
                "bluetooth.requestDevice" -> withBluetooth(fail) {
                    val services = p.optJSONArray("services")?.let { a -> List(a.length()) { BleUuids.parse(a.optString(it)) } }.orEmpty()
                    bt.requestDevice(services, p.optString("namePrefix").ifEmpty { null }) { r -> r.fold(ok) { fail(it.message ?: "ошибка") } }
                }
                "bluetooth.connect" -> withBluetooth(fail) { bt.connect(p.optString("device")) { r -> r.fold(ok) { fail(it.message ?: "ошибка") } } }
                "bluetooth.disconnect" -> { require("bluetooth"); bt.disconnect(p.optString("device")); ok(true) }
                "bluetooth.read" -> withBluetooth(fail) {
                    bt.read(p.optString("device"), p.optString("service"), p.optString("characteristic")) { r -> r.fold(ok) { fail(it.message ?: "ошибка") } }
                }
                "bluetooth.write" -> withBluetooth(fail) {
                    bt.write(p.optString("device"), p.optString("service"), p.optString("characteristic"), BleUuids.decode(p.optString("value")),
                        p.optBoolean("withoutResponse")) { r -> r.fold(ok) { fail(it.message ?: "ошибка") } }
                }
                "bluetooth.notifications" -> withBluetooth(fail) {
                    bt.setNotifications(p.optString("device"), p.optString("service"), p.optString("characteristic"),
                        p.optBoolean("enable", true)) { r -> r.fold(ok) { fail(it.message ?: "ошибка") } }
                }
                "bluetooth.serial.requestDevice" -> withBluetooth(fail) { bt.requestSerialDevice { r -> r.fold(ok) { fail(it.message ?: "ошибка") } } }
                "bluetooth.serial.connect" -> withBluetooth(fail) { bt.serialConnect(p.optString("device")) { r -> r.fold(ok) { fail(it.message ?: "ошибка") } } }
                "bluetooth.serial.write" -> withBluetooth(fail) {
                    bt.serialWrite(p.optString("device"), BleUuids.decode(p.optString("value"))) { r -> r.fold(ok) { fail(it.message ?: "ошибка") } }
                }
                "bluetooth.serial.disconnect" -> { require("bluetooth"); bt.serialDisconnect(p.optString("device")); ok(true) }

                "headphones.state" -> { require("headphones"); ok(audio.state()) }
                "headphones.captureButtons" -> { require("headphones"); audio.setCaptureMedia(p.optBoolean("enable", true)); ok(true) }
                "buttons.captureVolume" -> { require("buttons"); audio.captureVolume = p.optBoolean("enable", true); ok(true) }

                "screen.orientation" -> { require("screen"); requestedOrientation = orientationOf(p.optString("orientation", "any")); ok(true) }

                "player.name" -> withPlayerName { ok(it) }
                "scores.submit" -> {
                    require("scores")
                    val score = p.optDouble("score")
                    if (!score.isFinite()) return fail("score должен быть числом")
                    val level = p.optString("level").ifEmpty { null }
                    withPlayerName { player ->
                        val r = state.submit(score, player, level)
                        ok(JSONObject().put("best", r.best?.let(::scoreJson) ?: JSONObject.NULL).put("rank", r.rank).put("isRecord", r.isRecord))
                    }
                }
                "scores.top" -> {
                    require("scores")
                    val list = state.top(p.optInt("limit", 10), p.optString("level").ifEmpty { null })
                    ok(JSONArray().apply { list.forEach { put(scoreJson(it)) } })
                }
                else -> fail("неизвестный метод «${msg.optString("method")}»")
            }
        } catch (e: SecurityException) {
            fail(e.message ?: "нет разрешения")
        } catch (e: Exception) {
            fail(e.message ?: e.toString())
        }
    }

    /** Разрешение должно быть объявлено в manifest.json — иначе приложение его не получит. */
    private fun require(permission: String) {
        if (!manifest.has(permission)) throw SecurityException("нет разрешения «$permission» в manifest.json")
    }

    private fun reply(id: Int, result: Any?, error: String?) {
        val msg = JSONObject().put("id", id)
        if (error != null) msg.put("error", error) else msg.put("result", result ?: JSONObject.NULL)
        post(msg)
    }

    private fun sendEvent(event: String, data: Any?) {
        post(JSONObject().put("event", event).put("data", data ?: JSONObject.NULL))
    }

    private fun post(msg: JSONObject) {
        val p = proxy ?: return
        runCatching { p.postMessage(msg.toString()) }
    }

    private fun appInfo() = JSONObject()
        .put("id", manifest.id)
        .put("name", manifest.name)
        .put("version", manifest.version)
        .put("native", true)
        .put("platform", "android")
        .put("permissions", JSONArray(manifest.permissions.toList()))
        .put("scoreOrder", manifest.scoreOrder)
        .put("scoreUnit", manifest.scoreUnit)
        .put("player", Apps.playerName(this) ?: JSONObject.NULL)
        .put("sensors", JSONArray(if (manifest.has("sensors")) sensors.available() else emptyList()))

    private fun scoreJson(s: AppState.Score) = JSONObject()
        .put("score", s.score).put("player", s.player).put("time", s.time).put("level", s.level ?: JSONObject.NULL)

    private fun sensorEvent(type: String, values: FloatArray, ts: Long) = JSONObject()
        .put("type", type)
        .put("values", JSONArray().apply { values.forEach { put(it.toDouble()) } })
        .put("timestamp", ts / 1_000_000.0)
        .put("rotation", rotationDegrees())

    @Suppress("DEPRECATION")
    private fun rotationDegrees() = (if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) display?.rotation else windowManager.defaultDisplay.rotation)
        .let { (it ?: 0) * 90 }

    // ------------------------------------------------------------------ разрешения

    private fun permissionStatus(name: String): String = when {
        !manifest.has(name) -> "denied"
        name !in AppManifest.RUNTIME -> "granted"
        state.permission(name) == true && androidGranted(name) -> "granted"
        state.permission(name) == false -> "denied"
        else -> "prompt"
    }

    private fun androidPerms(name: String) = when (name) {
        "camera" -> arrayOf(Manifest.permission.CAMERA)
        "microphone" -> arrayOf(Manifest.permission.RECORD_AUDIO)
        "geolocation" -> arrayOf(Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION)
        // до Android 12 поиск Bluetooth-устройств требовал разрешения на местоположение
        "bluetooth" -> if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            arrayOf(Manifest.permission.BLUETOOTH_SCAN, Manifest.permission.BLUETOOTH_CONNECT)
        } else {
            arrayOf(Manifest.permission.ACCESS_FINE_LOCATION)
        }
        else -> emptyArray()
    }

    /**
     * Перед любой Bluetooth-операцией: разрешение в manifest.json, согласие пользователя,
     * разрешение Android и включённый Bluetooth (если выключен — предложим включить).
     * Ошибки внутри action (неверный UUID, нет подключения) тоже уходят в fail.
     */
    @SuppressLint("MissingPermission") // ACTION_REQUEST_ENABLE вызывается только после ensurePermission("bluetooth")
    private fun withBluetooth(fail: (String) -> Unit, action: () -> Unit) {
        require("bluetooth")
        val run = {
            try { action() } catch (e: Exception) { fail(e.message ?: e.toString()) }
        }
        ensurePermission("bluetooth") { granted ->
            when {
                !granted -> fail("пользователь не разрешил доступ к Bluetooth")
                !bt.supported() -> fail("на этом телефоне нет Bluetooth")
                bt.enabled() -> run()
                else -> {
                    pendingBtEnable = { on -> if (on) run() else fail("Bluetooth выключен") }
                    try {
                        @Suppress("DEPRECATION")
                        startActivityForResult(Intent(android.bluetooth.BluetoothAdapter.ACTION_REQUEST_ENABLE), REQ_BT_ENABLE)
                    } catch (e: Exception) {
                        pendingBtEnable = null
                        fail("включите Bluetooth в настройках телефона")
                    }
                }
            }
        }
    }

    @Deprecated("Deprecated in Java")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        @Suppress("DEPRECATION")
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == REQ_BT_ENABLE) {
            pendingBtEnable?.invoke(bt.enabled())
            pendingBtEnable = null
        }
    }

    private fun androidGranted(name: String) = androidPerms(name).all { checkSelfPermission(it) == PackageManager.PERMISSION_GRANTED }

    /**
     * Спросить пользователя (один раз — ответ запоминается) и, если нужно, получить разрешение Android.
     * Обрабатывает разрешения по очереди, чтобы не показывать несколько окон сразу.
     */
    private fun requestPermissions(names: List<String>, done: (Map<String, Boolean>) -> Unit) {
        val result = linkedMapOf<String, Boolean>()
        fun next(i: Int) {
            if (i == names.size) return done(result)
            val name = names[i]
            ensurePermission(name) { granted -> result[name] = granted; next(i + 1) }
        }
        next(0)
    }

    private fun ensurePermission(name: String, then: (Boolean) -> Unit) {
        if (!manifest.has(name)) return then(false)
        if (name !in AppManifest.RUNTIME) return then(true)
        val ask = { askAndroid(name, then) }
        when (state.permission(name)) {
            true -> ask()
            false -> then(false)
            null -> AlertDialog.Builder(this)
                .setTitle(manifest.name)
                .setMessage("Разрешить доступ: ${AppManifest.PERMISSIONS[name]}?")
                .setPositiveButton("Разрешить") { _, _ -> state.setPermission(name, true); ask() }
                .setNegativeButton("Запретить") { _, _ -> state.setPermission(name, false); then(false) }
                .setOnCancelListener { then(false) }
                .show()
        }
    }

    private fun askAndroid(name: String, then: (Boolean) -> Unit) {
        val missing = androidPerms(name).filter { checkSelfPermission(it) != PackageManager.PERMISSION_GRANTED }
        if (missing.isEmpty()) return then(true)
        // для геолокации хватит примерного местоположения, остальным нужны все разрешения (Bluetooth: поиск + подключение)
        pendingAndroid = { anyGranted -> then(if (name == "geolocation") anyGranted else androidGranted(name)) }
        requestPermissions(missing.toTypedArray(), REQ_PERMS)
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, results: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, results)
        if (requestCode != REQ_PERMS) return
        // для геолокации достаточно хотя бы примерного местоположения
        val ok = results.isNotEmpty() && results.any { it == PackageManager.PERMISSION_GRANTED }
        pendingAndroid?.invoke(ok)
        pendingAndroid = null
    }

    // ------------------------------------------------------------------ имя игрока

    private fun withPlayerName(then: (String) -> Unit) {
        Apps.playerName(this)?.let { return then(it) }
        val input = EditText(this).apply { hint = "Игрок"; setSingleLine(); setPadding(48, 32, 48, 32) }
        AlertDialog.Builder(this)
            .setTitle("Ваше имя для таблицы рекордов")
            .setView(input)
            .setPositiveButton("Сохранить") { _, _ ->
                val name = input.text.toString().trim().ifEmpty { "Игрок" }
                Apps.setPlayerName(this, name)
                then(name)
            }
            .setOnCancelListener { then("Игрок") }
            .show()
    }

    // ------------------------------------------------------------------ WebView

    private inner class Client : WebViewClient() {
        override fun shouldInterceptRequest(view: WebView, request: WebResourceRequest): WebResourceResponse? {
            val uri = request.url
            if (server.isAppUrl(uri)) return server.serve(uri)
            // без разрешения «network» приложение работает только с собственными файлами
            if (!manifest.has("network") && (uri.scheme == "http" || uri.scheme == "https")) return AppServer.error(403, "Forbidden")
            return null
        }

        override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
            val uri = request.url
            if (server.isAppUrl(uri)) return false
            // внешние ссылки открываются в обычном браузере, а приложение остаётся приложением
            openInBrowser(uri)
            return true
        }

        override fun onRenderProcessGone(view: WebView, detail: android.webkit.RenderProcessGoneDetail): Boolean {
            Toast.makeText(this@AppActivity, "Приложение аварийно завершилось", Toast.LENGTH_LONG).show()
            finishAndRemoveTask()
            return true
        }
    }

    private fun openInBrowser(uri: Uri) {
        if (uri.scheme == "http" || uri.scheme == "https") {
            startActivity(Intent(this, MainActivity::class.java).setAction(Intent.ACTION_VIEW).setData(uri))
        } else {
            runCatching { startActivity(Intent(Intent.ACTION_VIEW, uri).addCategory(Intent.CATEGORY_BROWSABLE)) }
        }
    }

    private inner class Chrome : WebChromeClient() {
        override fun onPermissionRequest(request: PermissionRequest) {
            val names = request.resources.mapNotNull {
                when (it) {
                    PermissionRequest.RESOURCE_VIDEO_CAPTURE -> "camera"
                    PermissionRequest.RESOURCE_AUDIO_CAPTURE -> "microphone"
                    else -> null
                }
            }
            if (names.isEmpty() || request.origin.toString().trimEnd('/') != manifest.origin) return request.deny()
            requestPermissions(names) { r -> if (r.values.all { it }) request.grant(request.resources) else request.deny() }
        }

        override fun onGeolocationPermissionsShowPrompt(origin: String, callback: GeolocationPermissions.Callback) {
            if (origin.trimEnd('/') != manifest.origin) return callback.invoke(origin, false, false)
            ensurePermission("geolocation") { ok -> callback.invoke(origin, ok, false) }
        }

        override fun onShowCustomView(view: View, callback: CustomViewCallback) {
            fullscreenView = view
            fullscreenCallback = callback
            (window.decorView as FrameLayout).addView(view, FrameLayout.LayoutParams(-1, -1))
        }

        override fun onHideCustomView() {
            fullscreenView?.let { (window.decorView as FrameLayout).removeView(it) }
            fullscreenView = null
            fullscreenCallback = null
        }
    }

    // ------------------------------------------------------------------ экран

    private fun hideSystemBars() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            @Suppress("DEPRECATION") window.setDecorFitsSystemWindows(false)
            window.insetsController?.let {
                it.hide(WindowInsets.Type.systemBars())
                it.systemBarsBehavior = WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
            }
        } else {
            @Suppress("DEPRECATION")
            window.decorView.systemUiVisibility = View.SYSTEM_UI_FLAG_FULLSCREEN or View.SYSTEM_UI_FLAG_HIDE_NAVIGATION or
                View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY or View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN or
                View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION or View.SYSTEM_UI_FLAG_LAYOUT_STABLE
        }
    }

    private fun orientationOf(o: String) = when (o) {
        "portrait" -> ActivityInfo.SCREEN_ORIENTATION_SENSOR_PORTRAIT
        "landscape" -> ActivityInfo.SCREEN_ORIENTATION_SENSOR_LANDSCAPE
        else -> ActivityInfo.SCREEN_ORIENTATION_FULL_USER
    }

    /** Название и иконка приложения в списке недавних. */
    private fun setRecentsCard() {
        val icon = Apps.iconBitmap(this, manifest)
        @Suppress("DEPRECATION")
        setTaskDescription(ActivityManager.TaskDescription(manifest.name, icon))
    }

    companion object {
        private const val REQ_PERMS = 10
        private const val REQ_BT_ENABLE = 11
    }
}
