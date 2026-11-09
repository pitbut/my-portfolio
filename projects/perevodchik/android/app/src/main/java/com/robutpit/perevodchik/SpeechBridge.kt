package com.robutpit.perevodchik

import android.content.Intent
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

    @JavascriptInterface
    fun isRecognitionAvailable(): Boolean = SpeechRecognizer.isRecognitionAvailable(activity)

    @JavascriptInterface
    fun startListening(id: Int, lang: String) = main.post {
        session = id
        val rec = recognizer ?: SpeechRecognizer.createSpeechRecognizer(activity).also { recognizer = it }
        rec.cancel()
        rec.setRecognitionListener(Listener(id))
        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, lang)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_PREFERENCE, lang)
            putExtra("android.speech.extra.EXTRA_ADDITIONAL_LANGUAGES", arrayOf(lang))
            putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
            putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
            putExtra(RecognizerIntent.EXTRA_CALLING_PACKAGE, activity.packageName)
            putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS, 1200L)
        }
        try {
            rec.startListening(intent)
        } catch (e: Exception) {
            js("window.nativeSpeech && nativeSpeech.error($id, 'aborted'); window.nativeSpeech && nativeSpeech.end($id)")
        }
    }

    @JavascriptInterface
    fun stopListening() = main.post {
        session = -1
        recognizer?.cancel()
    }

    private inner class Listener(private val id: Int) : RecognitionListener {
        private var finished = false
        private fun cb(fn: String, arg: String? = null) {
            val a = if (arg == null) "" else ", " + JSONObject.quote(arg)
            js("window.nativeSpeech && nativeSpeech.$fn($id$a)")
        }
        private fun text(b: Bundle?) =
            b?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull().orEmpty()

        override fun onReadyForSpeech(params: Bundle?) {}
        override fun onBeginningOfSpeech() {}
        override fun onRmsChanged(rmsdB: Float) {}
        override fun onBufferReceived(buffer: ByteArray?) {}
        override fun onEndOfSpeech() {}
        override fun onEvent(eventType: Int, params: Bundle?) {}

        override fun onPartialResults(partialResults: Bundle?) {
            val t = text(partialResults)
            if (t.isNotBlank()) cb("partial", t)
        }

        override fun onResults(results: Bundle?) {
            if (finished) return; finished = true
            val t = text(results)
            if (t.isNotBlank()) cb("final", t)
            cb("end")
        }

        override fun onError(error: Int) {
            if (finished) return; finished = true
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
        recognizer?.destroy(); recognizer = null
        tts?.shutdown(); tts = null
    }
}
