package com.robutpit.roachrace.sensors

import android.content.Context
import android.media.AudioAttributes
import android.media.SoundPool
import com.robutpit.roachrace.R

/** Two short synthesised sound effects (no recordings, generated PCM —
 * see the raw/ WAVs): a generic footstep-ish tap for running roaches, and a
 * hiss specifically for the Madagascar hissing cockroach — real ones
 * actually hiss by forcing air through their spiracles when startled, which
 * lines up neatly with this game's existing "spooked" event. */
class GameAudio(context: Context) {
    private val pool = SoundPool.Builder()
        .setMaxStreams(6)
        .setAudioAttributes(
            AudioAttributes.Builder()
                .setUsage(AudioAttributes.USAGE_GAME)
                .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                .build(),
        )
        .build()

    private val tapId = pool.load(context, R.raw.tap, 1)
    private val hissId = pool.load(context, R.raw.hiss, 1)

    fun playTap(volume: Float = 0.35f) {
        pool.play(tapId, volume, volume, 0, 0, 1f)
    }

    fun playHiss(volume: Float = 0.55f) {
        pool.play(hissId, volume, volume, 1, 0, 1f)
    }

    fun release() {
        pool.release()
    }
}
