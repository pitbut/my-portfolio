package com.robutpit.pitbrowser.apps

import android.app.Activity
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.media.AudioDeviceCallback
import android.media.AudioDeviceInfo
import android.media.AudioManager
import android.media.session.MediaSession
import android.media.session.PlaybackState
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.view.KeyEvent
import org.json.JSONArray
import org.json.JSONObject

/**
 * Наушники и аппаратные кнопки для PitSDK:
 * - какие наушники подключены (проводные, Bluetooth, USB), есть ли у них микрофон;
 * - события подключения/отключения и «наушники выдернули» (пора ставить звук на паузу);
 * - кнопки гарнитуры (пауза, следующий/предыдущий трек) — проводной и Bluetooth;
 * - кнопки громкости телефона как игровые кнопки (по запросу приложения).
 */
class AudioBridge(
    private val activity: Activity,
    private val emit: (event: String, data: JSONObject) -> Unit,
) {
    private val am = activity.getSystemService(Context.AUDIO_SERVICE) as AudioManager
    private val main = Handler(Looper.getMainLooper())

    /** Приложение хочет получать кнопки гарнитуры / кнопки громкости. */
    var captureMedia = false
        private set
    var captureVolume = false

    private var session: MediaSession? = null
    private var listening = false
    private var ready = false // первое срабатывание колбэка — это уже подключённые устройства, не событие

    private val deviceCallback = object : AudioDeviceCallback() {
        override fun onAudioDevicesAdded(added: Array<out AudioDeviceInfo>) = changed(added, "connected")
        override fun onAudioDevicesRemoved(removed: Array<out AudioDeviceInfo>) = changed(removed, "disconnected")
    }

    private val noisyReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) {
            if (intent.action == AudioManager.ACTION_AUDIO_BECOMING_NOISY) emit("headphones:unplugged", JSONObject())
        }
    }

    private fun changed(devices: Array<out AudioDeviceInfo>, change: String) {
        if (!ready || devices.none { typeName(it.type) != null }) return
        emit("headphones", state().put("change", change))
    }

    /** Начать следить за подключением наушников. */
    fun start() {
        if (listening) return
        listening = true
        ready = false
        am.registerAudioDeviceCallback(deviceCallback, main)
        main.post { ready = true }
        val filter = IntentFilter(AudioManager.ACTION_AUDIO_BECOMING_NOISY)
        // системная рассылка: доходит и до «неэкспортированного» получателя
        if (Build.VERSION.SDK_INT >= 33) activity.registerReceiver(noisyReceiver, filter, Context.RECEIVER_NOT_EXPORTED)
        else activity.registerReceiver(noisyReceiver, filter)
    }

    fun state(): JSONObject {
        val outputs = am.getDevices(AudioManager.GET_DEVICES_OUTPUTS)
        val inputs = am.getDevices(AudioManager.GET_DEVICES_INPUTS)
        // Bluetooth-наушники видны дважды (A2DP — музыка, SCO — звонки): объединяем по имени
        val byKey = linkedMapOf<String, JSONObject>()
        for (d in outputs) {
            val type = typeName(d.type) ?: continue
            val name = d.productName?.toString()?.takeIf { it.isNotBlank() && it != android.os.Build.MODEL } ?: defaultName(type)
            val key = "$type|$name"
            if (key in byKey) continue
            val mic = inputs.any { i -> typeName(i.type) == type && (type == "wired" || i.productName == d.productName) } ||
                d.type == AudioDeviceInfo.TYPE_WIRED_HEADSET
            byKey[key] = JSONObject().put("type", type).put("name", name).put("microphone", mic)
        }
        val list = JSONArray(byKey.values.toList())
        return JSONObject().put("connected", list.length() > 0).put("devices", list)
    }

    private fun typeName(t: Int): String? = when (t) {
        AudioDeviceInfo.TYPE_WIRED_HEADPHONES, AudioDeviceInfo.TYPE_WIRED_HEADSET -> "wired"
        AudioDeviceInfo.TYPE_BLUETOOTH_A2DP, AudioDeviceInfo.TYPE_BLUETOOTH_SCO -> "bluetooth"
        else -> when {
            Build.VERSION.SDK_INT >= 26 && t == AudioDeviceInfo.TYPE_USB_HEADSET -> "usb"
            Build.VERSION.SDK_INT >= 28 && t == AudioDeviceInfo.TYPE_HEARING_AID -> "hearing_aid"
            Build.VERSION.SDK_INT >= 31 && t == AudioDeviceInfo.TYPE_BLE_HEADSET -> "bluetooth"
            else -> null
        }
    }

    private fun defaultName(type: String) = when (type) {
        "wired" -> "Проводные наушники"
        "bluetooth" -> "Bluetooth-наушники"
        "usb" -> "USB-наушники"
        else -> "Слуховой аппарат"
    }

    // ------------------------------------------------------------------ кнопки

    /**
     * Кнопки гарнитуры. Проводные приходят как нажатия клавиш (onKey), Bluetooth (AVRCP) —
     * через медиа-сессию, поэтому, пока приложение на экране, создаём её и делаем активной.
     */
    fun setCaptureMedia(enable: Boolean) {
        captureMedia = enable
        if (enable) {
            val s = session ?: MediaSession(activity, "PitApp").also { session = it }
            s.setCallback(object : MediaSession.Callback() {
                override fun onMediaButtonEvent(intent: Intent): Boolean {
                    @Suppress("DEPRECATION")
                    val e = if (Build.VERSION.SDK_INT >= 33) intent.getParcelableExtra(Intent.EXTRA_KEY_EVENT, KeyEvent::class.java)
                    else intent.getParcelableExtra(Intent.EXTRA_KEY_EVENT)
                    return e != null && onKey(e, "headset")
                }
            }, main)
            s.setPlaybackState(
                PlaybackState.Builder()
                    .setActions(PlaybackState.ACTION_PLAY_PAUSE or PlaybackState.ACTION_PLAY or PlaybackState.ACTION_PAUSE or
                        PlaybackState.ACTION_SKIP_TO_NEXT or PlaybackState.ACTION_SKIP_TO_PREVIOUS or PlaybackState.ACTION_STOP)
                    .setState(PlaybackState.STATE_PLAYING, 0, 1f)
                    .build(),
            )
            s.isActive = true
        } else {
            session?.isActive = false
        }
    }

    /** Нажатие клавиши (из Activity или медиа-сессии). true — событие отдано приложению и поглощено. */
    fun onKey(e: KeyEvent, source: String = "phone"): Boolean {
        val button = MEDIA_KEYS[e.keyCode]
        val isVolume = e.keyCode == KeyEvent.KEYCODE_VOLUME_UP || e.keyCode == KeyEvent.KEYCODE_VOLUME_DOWN
        val wanted = (button != null && captureMedia) || (isVolume && captureVolume)
        if (!wanted) return false
        if (e.action == KeyEvent.ACTION_DOWN && e.repeatCount > 0) return true // автоповтор при удержании не шлём
        val name = button ?: if (e.keyCode == KeyEvent.KEYCODE_VOLUME_UP) "volume_up" else "volume_down"
        val action = if (e.action == KeyEvent.ACTION_DOWN) "down" else "up"
        emit("button", JSONObject().put("button", name).put("action", action).put("source", if (isVolume) "phone" else source))
        return true
    }

    /** Приложение свернули — кнопки возвращаются плееру, а не игре. */
    fun pause() { session?.isActive = false }

    fun resume() { if (captureMedia) session?.isActive = true }

    fun release() {
        if (listening) {
            runCatching { am.unregisterAudioDeviceCallback(deviceCallback) }
            runCatching { activity.unregisterReceiver(noisyReceiver) }
            listening = false
        }
        session?.release()
        session = null
    }

    companion object {
        private val MEDIA_KEYS = mapOf(
            KeyEvent.KEYCODE_HEADSETHOOK to "play_pause",
            KeyEvent.KEYCODE_MEDIA_PLAY_PAUSE to "play_pause",
            KeyEvent.KEYCODE_MEDIA_PLAY to "play",
            KeyEvent.KEYCODE_MEDIA_PAUSE to "pause",
            KeyEvent.KEYCODE_MEDIA_NEXT to "next",
            KeyEvent.KEYCODE_MEDIA_PREVIOUS to "previous",
            KeyEvent.KEYCODE_MEDIA_STOP to "stop",
            KeyEvent.KEYCODE_MEDIA_FAST_FORWARD to "fast_forward",
            KeyEvent.KEYCODE_MEDIA_REWIND to "rewind",
        )
    }
}
