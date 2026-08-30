package com.robutpit.zamri.tts

import android.content.Context
import android.speech.tts.TextToSpeech
import com.robutpit.zamri.data.db.ViolationSide
import com.robutpit.zamri.motion.SectorLabel
import java.util.Locale
import java.util.UUID

/**
 * Wraps [TextToSpeech] to announce the doll's phrases: phase changes and,
 * critically, violator positions ("Слева, второй!") generated on the fly
 * from the sector number - no pre-recorded clip per lane is needed.
 */
class VoiceAnnouncer(context: Context) {

    private var ready = false
    private val pending = mutableListOf<String>()
    private var tts: TextToSpeech? = null

    init {
        tts = TextToSpeech(context.applicationContext) { status ->
            if (status == TextToSpeech.SUCCESS) {
                ready = true
                tts?.language = Locale.forLanguageTag("ru-RU")
                pending.forEach { speakNow(it) }
                pending.clear()
            }
        }
    }

    var volume: Float = 1f

    fun speakPhase(isGreen: Boolean) {
        speak(if (isGreen) "Зелёный свет!" else "Красный свет! Не двигаться!")
    }

    fun speakFinish() {
        speak("Игра окончена! Спасибо за игру!")
    }

    fun speakViolation(label: SectorLabel) {
        val phrase = when (label.side) {
            ViolationSide.CENTER -> "По центру!"
            ViolationSide.LEFT -> laneOrdinal("Слева", label.sideLane)
            ViolationSide.RIGHT -> laneOrdinal("Справа", label.sideLane)
        }
        speak(phrase)
    }

    private fun laneOrdinal(sideWord: String, lane: Int): String {
        val ordinal = when (lane) {
            1 -> "первый"
            2 -> "второй"
            3 -> "третий"
            4 -> "четвёртый"
            else -> "$lane-й"
        }
        return "$sideWord, $ordinal!"
    }

    private fun speak(text: String) {
        if (!ready) {
            pending += text
            return
        }
        speakNow(text)
    }

    private fun speakNow(text: String) {
        val params = android.os.Bundle().apply {
            putFloat(TextToSpeech.Engine.KEY_PARAM_VOLUME, volume.coerceIn(0f, 1f))
        }
        tts?.speak(text, TextToSpeech.QUEUE_FLUSH, params, UUID.randomUUID().toString())
    }

    fun shutdown() {
        tts?.stop()
        tts?.shutdown()
        tts = null
    }
}
