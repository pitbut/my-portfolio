package com.robutpit.roachrace.sensors

import android.Manifest
import android.annotation.SuppressLint
import android.content.Context
import android.content.pm.PackageManager
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import androidx.core.content.ContextCompat
import kotlin.math.sqrt

/**
 * Samples microphone RMS level on a background thread and reports peaks
 * no more often than [cooldownMs]. Instead of one fixed magnitude threshold
 * (unreliable across phones — mic gain/AGC varies a lot), it tracks a
 * rolling ambient-noise floor and fires when the level spikes well above
 * *that phone's own* recent baseline, mirroring the Web Audio API
 * amplitude-peak trick used by the browser prototype but adaptive.
 */
class MicListener(
    private val context: Context,
    private val onLevel: (Float) -> Unit,
    private val onPeak: () -> Unit,
) {
    private var record: AudioRecord? = null
    private var thread: Thread? = null
    @Volatile private var running = false
    private var lastPeakAt = 0L
    private var ambient = 0.01f
    private val cooldownMs = 1000L

    fun hasPermission(): Boolean =
        ContextCompat.checkSelfPermission(context, Manifest.permission.RECORD_AUDIO) ==
            PackageManager.PERMISSION_GRANTED

    @SuppressLint("MissingPermission")
    fun start(): Boolean {
        if (!hasPermission() || running) return false
        val sampleRate = 16000
        val minBuf = AudioRecord.getMinBufferSize(
            sampleRate, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT
        )
        if (minBuf <= 0) return false
        val bufSize = minBuf * 2
        val rec = AudioRecord(
            MediaRecorder.AudioSource.MIC, sampleRate,
            AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT, bufSize
        )
        if (rec.state != AudioRecord.STATE_INITIALIZED) {
            rec.release()
            return false
        }
        record = rec
        running = true
        ambient = 0.01f
        rec.startRecording()
        thread = Thread {
            val buf = ShortArray(bufSize / 2)
            while (running) {
                val n = rec.read(buf, 0, buf.size)
                if (n > 0) {
                    var sum = 0.0
                    for (i in 0 until n) {
                        val v = buf[i] / 32768.0
                        sum += v * v
                    }
                    val rms = sqrt(sum / n).toFloat()
                    onLevel((rms / 0.35f).coerceIn(0f, 1f))
                    val now = System.currentTimeMillis()
                    val isPeak = rms > ambient * 2.4f + 0.018f
                    if (isPeak && now - lastPeakAt > cooldownMs) {
                        lastPeakAt = now
                        onPeak()
                    }
                    if (!isPeak) {
                        ambient = ambient * 0.97f + rms * 0.03f
                    }
                }
            }
        }
        thread?.start()
        return true
    }

    fun stop() {
        running = false
        thread?.join(200)
        thread = null
        try {
            record?.stop()
        } catch (_: Exception) {
        }
        record?.release()
        record = null
    }
}
