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
 * above [threshold] no more often than [cooldownMs], mirroring the Web
 * Audio API amplitude-peak trick used by the browser prototype.
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
    private val threshold = 0.28f
    private val cooldownMs = 1400L

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
                    onLevel(rms)
                    val now = System.currentTimeMillis()
                    if (rms > threshold && now - lastPeakAt > cooldownMs) {
                        lastPeakAt = now
                        onPeak()
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
