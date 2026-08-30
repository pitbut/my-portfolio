package com.robutpit.zamri.audio

import android.content.Context
import android.media.AudioAttributes
import android.media.AudioManager
import android.media.SoundPool
import com.robutpit.zamri.R

enum class Cue { GREEN_START, RED_START, VIOLATION }

/**
 * Plays the short pre-rendered start/stop/violation stingers from res/raw
 * through STREAM_MUSIC. Kept separate from [com.robutpit.zamri.tts.VoiceAnnouncer]
 * so the phase-change "beep" has zero TTS engine latency at the critical
 * green->red transition instant.
 */
class SoundCues(context: Context) {

    private val audioManager = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager

    private val soundPool = SoundPool.Builder()
        .setMaxStreams(3)
        .setAudioAttributes(
            AudioAttributes.Builder()
                .setUsage(AudioAttributes.USAGE_GAME)
                .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                .build()
        )
        .build()

    private val soundIds = mapOf(
        Cue.GREEN_START to soundPool.load(context, R.raw.cue_green, 1),
        Cue.RED_START to soundPool.load(context, R.raw.cue_red, 1),
        Cue.VIOLATION to soundPool.load(context, R.raw.cue_violation, 1)
    )

    var volume: Float = 1f

    fun play(cue: Cue) {
        val id = soundIds[cue] ?: return
        soundPool.play(id, volume, volume, 1, 0, 1f)
    }

    /** Sets STREAM_MUSIC to a fraction (0..1) of its max index, per the settings slider. */
    fun applyStreamVolume(fraction: Float) {
        val max = audioManager.getStreamMaxVolume(AudioManager.STREAM_MUSIC)
        val target = (max * fraction.coerceIn(0f, 1f)).toInt()
        runCatching {
            audioManager.setStreamVolume(AudioManager.STREAM_MUSIC, target, 0)
        }
    }

    fun release() {
        soundPool.release()
    }
}
