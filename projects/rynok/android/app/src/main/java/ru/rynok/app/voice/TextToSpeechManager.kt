package ru.rynok.app.voice

import android.content.Context
import android.speech.tts.TextToSpeech
import java.util.Locale
import java.util.UUID

/**
 * Обёртка над Android TextToSpeech — озвучивает "что осталось купить" и
 * итог по бюджету (перерасход/экономия), когда у мужа заняты руки.
 */
class TextToSpeechManager(context: Context) {

    private var tts: TextToSpeech? = null
    private var ready = false
    private val pendingQueue = mutableListOf<String>()

    init {
        tts = TextToSpeech(context.applicationContext) { status ->
            if (status == TextToSpeech.SUCCESS) {
                tts?.language = Locale("ru", "RU")
                ready = true
                pendingQueue.forEach { speakNow(it) }
                pendingQueue.clear()
            }
        }
    }

    fun speak(text: String) {
        if (ready) speakNow(text) else pendingQueue.add(text)
    }

    private fun speakNow(text: String) {
        tts?.speak(text, TextToSpeech.QUEUE_FLUSH, null, UUID.randomUUID().toString())
    }

    fun shutdown() {
        tts?.stop()
        tts?.shutdown()
        tts = null
    }
}
