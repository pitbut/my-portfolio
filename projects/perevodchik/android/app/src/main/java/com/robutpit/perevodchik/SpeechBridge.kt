package com.robutpit.perevodchik

import android.content.Intent
import android.media.AudioFormat
import android.os.Build
import android.os.ParcelFileDescriptor
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import android.webkit.JavascriptInterface
import android.webkit.WebView
import org.json.JSONObject
import java.util.Locale

/**
 * Мост JavaScript ↔ Android: распознавание речи (SpeechRecognizer) и озвучка (TextToSpeech).
 * Из JS доступен как window.AndroidBridge, ответы приходят в window.nativeSpeech / window.nativeTts.
 */
class SpeechBridge(private val activity: MainActivity, private val web: WebView) {

    private val main = Handler(Looper.getMainLooper())
    private var recognizer: SpeechRecognizer? = null
    private var session = 0          // номер текущей сессии распознавания (старые ответы игнорируются в JS)
    private var tts: TextToSpeech? = null
    @Volatile private var ttsReady = false

    /* Усиление микрофона (Android 13+). Если распознаватель телефона не принимает наш звук,
       сами переходим на обычный режим и больше не пытаемся до перезапуска. */
    private val booster = MicBooster { level -> js("window.nativeSpeech && nativeSpeech.level($level)") }
    private var boostEnabled = true
    private var boostBroken = false
    private var boostProven = false // хоть раз распознал наш звук — значит, поддерживается
    private var deafSessions = 0  // сессий подряд: микрофон слышал речь, а распознаватель — нет
    private val boostSupported get() = Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU
    private val useBoost get() = boostSupported && boostEnabled && !boostBroken && activity.hasMic()

    init {
        main.post {
            tts = TextToSpeech(activity) { status ->
                ttsReady = status == TextToSpeech.SUCCESS
            }.apply {
                setOnUtteranceProgressListener(object : UtteranceProgressListener() {
                    override fun onStart(id: String) {}
                    override fun onDone(id: String) = js("window.nativeTts && nativeTts.done(${JSONObject.quote(id)})")
                    @Deprecated("Deprecated in Java")
                    override fun onError(id: String) = js("window.nativeTts && nativeTts.done(${JSONObject.quote(id)})")
                    override fun onError(id: String, code: Int) = js("window.nativeTts && nativeTts.done(${JSONObject.quote(id)})")
                    override fun onStop(id: String, interrupted: Boolean) = js("window.nativeTts && nativeTts.done(${JSONObject.quote(id)})")
                })
            }
        }
    }

    fun js(code: String) { main.post { web.evaluateJavascript(code, null) } }

    /* ---------- Микрофон и экран ---------- */

    @JavascriptInterface fun hasMic(): Boolean = activity.hasMic()
    @JavascriptInterface fun requestMic() = activity.requestMic()
    @JavascriptInterface fun keepScreenOn(on: Boolean) = activity.keepScreenOn(on)

    /* ---------- Распознавание ---------- */

    /** Настройки микрофона из JS: усиление 1..6, подавление шума */
    @JavascriptInterface
    fun setMic(gain: Float, noiseSuppress: Boolean) = main.post {
        val nsChanged = booster.noiseSuppress != noiseSuppress
        booster.gain = gain.coerceIn(1f, 8f)
        booster.noiseSuppress = noiseSuppress
        boostEnabled = gain > 1.01f || noiseSuppress
        if (booster.isRunning && (nsChanged || !useBoost)) booster.stop() // перезапустится при следующей фразе
    }

    /** Можно ли усиливать звук для встроенного распознавания на этом телефоне */
    @JavascriptInterface
    fun canBoost(): Boolean = boostSupported && !boostBroken

    @JavascriptInterface
    fun isRecognitionAvailable(): Boolean = SpeechRecognizer.isRecognitionAvailable(activity)

    @JavascriptInterface
    fun startListening(id: Int, lang: String) = main.post {
        session = id
        val rec = recognizer ?: SpeechRecognizer.createSpeechRecognizer(activity).also { recognizer = it }
        rec.cancel()
        booster.detach()
        val boosted = useBoost && booster.start()
        rec.setRecognitionListener(Listener(id, boosted))
        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, lang)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_PREFERENCE, lang)
            putExtra("android.speech.extra.EXTRA_ADDITIONAL_LANGUAGES", arrayOf(lang))
            putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
            putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
            putExtra(RecognizerIntent.EXTRA_CALLING_PACKAGE, activity.packageName)
            putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS, 1200L)
            putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_POSSIBLY_COMPLETE_SILENCE_LENGTH_MILLIS, 1000L)
        }
        var readEnd: ParcelFileDescriptor? = null
        if (boosted && Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            val pipe = ParcelFileDescriptor.createPipe()
            readEnd = pipe[0]
            intent.putExtra(RecognizerIntent.EXTRA_AUDIO_SOURCE, pipe[0])
            intent.putExtra(RecognizerIntent.EXTRA_AUDIO_SOURCE_CHANNEL_COUNT, 1)
            intent.putExtra(RecognizerIntent.EXTRA_AUDIO_SOURCE_ENCODING, AudioFormat.ENCODING_PCM_16BIT)
            intent.putExtra(RecognizerIntent.EXTRA_AUDIO_SOURCE_SAMPLING_RATE, MicBooster.RATE)
            booster.attach(ParcelFileDescriptor.AutoCloseOutputStream(pipe[1]))
        } else if (booster.isRunning) {
            booster.stop()
        }
        try {
            rec.startListening(intent)
            readEnd?.close() // копию дескриптора распознаватель уже получил
        } catch (e: Exception) {
            if (boosted) boostFailed()
            js("window.nativeSpeech && nativeSpeech.error($id, 'aborted'); window.nativeSpeech && nativeSpeech.end($id)")
        }
    }

    @JavascriptInterface
    fun stopListening() = main.post {
        session = -1
        recognizer?.cancel()
        booster.stop()
    }

    private fun boostFailed() {
        if (boostBroken) return
        boostBroken = true
        booster.stop()
        js("window.nativeSpeech && nativeSpeech.boostUnsupported && nativeSpeech.boostUnsupported()")
    }

    private inner class Listener(private val id: Int, private val boosted: Boolean) : RecognitionListener {
        private var finished = false
        private fun cb(fn: String, arg: String? = null) {
            val a = if (arg == null) "" else ", " + JSONObject.quote(arg)
            js("window.nativeSpeech && nativeSpeech.$fn($id$a)")
        }
        private fun text(b: Bundle?) =
            b?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull().orEmpty()

        override fun onReadyForSpeech(params: Bundle?) {}
        override fun onBeginningOfSpeech() {}
        override fun onRmsChanged(rmsdB: Float) {
            // Без усиления индикатор громкости рисуем по данным распознавателя (≈ -2..10 дБ)
            if (!boosted) js("window.nativeSpeech && nativeSpeech.level(${((rmsdB + 2f) / 12f).coerceIn(0f, 1f) * 0.12f})")
        }
        override fun onBufferReceived(buffer: ByteArray?) {}
        override fun onEndOfSpeech() {}
        override fun onEvent(eventType: Int, params: Bundle?) {}

        override fun onPartialResults(partialResults: Bundle?) {
            val t = text(partialResults)
            if (t.isNotBlank()) cb("partial", t)
        }

        override fun onResults(results: Bundle?) {
            if (finished) return; finished = true
            if (boosted) { booster.detach(); deafSessions = 0; if (text(results).isNotBlank()) boostProven = true }
            val t = text(results)
            if (t.isNotBlank()) cb("final", t)
            cb("end")
        }

        override fun onError(error: Int) {
            if (finished) return; finished = true
            if (boosted) {
                booster.detach()
                val deaf = error == SpeechRecognizer.ERROR_CLIENT ||
                    ((error == SpeechRecognizer.ERROR_NO_MATCH || error == SpeechRecognizer.ERROR_SPEECH_TIMEOUT) &&
                        booster.sessionPeak > 0.1f)
                when {
                    // Распознаватель не смог взять звук — наш поток он не принимает
                    error == SpeechRecognizer.ERROR_AUDIO && !boostProven -> boostFailed()
                    // Микрофон явно слышал речь, а распознаватель — «тишина» 3 раза подряд → не поддерживает
                    deaf && !boostProven -> if (++deafSessions >= 3) boostFailed()
                    else -> deafSessions = 0
                }
            }
            val code = when (error) {
                SpeechRecognizer.ERROR_NO_MATCH, SpeechRecognizer.ERROR_SPEECH_TIMEOUT -> "no-speech"
                SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS -> "not-allowed"
                SpeechRecognizer.ERROR_NETWORK, SpeechRecognizer.ERROR_NETWORK_TIMEOUT,
                SpeechRecognizer.ERROR_SERVER -> "network"
                SpeechRecognizer.ERROR_RECOGNIZER_BUSY -> "busy"
                12, 13 -> "language-not-supported" // LANGUAGE_NOT_SUPPORTED / LANGUAGE_UNAVAILABLE (API 31+)
                else -> "aborted"
            }
            cb("error", code)
            cb("end")
        }
    }

    /* ---------- Озвучка ---------- */

    @JavascriptInterface
    fun hasVoice(lang: String): Boolean {
        val t = tts ?: return false
        if (!ttsReady) return true // ещё загружается — не пугаем пользователя
        return t.isLanguageAvailable(Locale.forLanguageTag(lang)) >= TextToSpeech.LANG_AVAILABLE
    }

    @JavascriptInterface
    fun speak(id: String, text: String, lang: String, rate: Float) = main.post {
        val t = tts
        if (t == null || !ttsReady) {
            js("window.nativeTts && nativeTts.done(${JSONObject.quote(id)})"); return@post
        }
        t.language = Locale.forLanguageTag(lang)
        t.setSpeechRate(rate)
        t.speak(text, TextToSpeech.QUEUE_FLUSH, null, id)
    }

    @JavascriptInterface
    fun stopSpeaking() = main.post { tts?.stop() }

    fun release() {
        booster.stop()
        recognizer?.destroy(); recognizer = null
        tts?.shutdown(); tts = null
    }
}
