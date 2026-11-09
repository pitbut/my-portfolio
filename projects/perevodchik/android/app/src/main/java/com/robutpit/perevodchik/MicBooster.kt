package com.robutpit.perevodchik

import android.annotation.SuppressLint
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.media.audiofx.NoiseSuppressor
import java.io.OutputStream
import kotlin.math.abs
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sqrt

/**
 * Свой захват микрофона с усилением — для распознавателя Android 13+ (EXTRA_AUDIO_SOURCE).
 *
 * Источник VOICE_RECOGNITION — без «телефонной» обработки, которая глушит дальние голоса.
 * Усиление с ограничителем: тихая речь поднимается, громкая не перегружается.
 * Последние ~0,4 с хранятся и отдаются в начало каждой новой сессии,
 * чтобы не терялся первый слог, пока распознаватель перезапускается.
 */
class MicBooster(private val onLevel: (Float) -> Unit) {

    @Volatile var gain = 3f
    @Volatile var noiseSuppress = false
    /** Максимальная громкость (0..1) с момента последнего attach — чтобы понять, слышал ли микрофон речь */
    @Volatile var sessionPeak = 0f
        private set

    private val lock = Object()
    private var out: OutputStream? = null
    private val preroll = ArrayDeque<ByteArray>()
    @Volatile private var running = false
    private var thread: Thread? = null

    val isRunning get() = running

    @SuppressLint("MissingPermission") // разрешение проверяется до запуска
    fun start(): Boolean {
        if (running) return true
        val minBuf = AudioRecord.getMinBufferSize(RATE, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT)
        if (minBuf <= 0) return false
        val rec = try {
            AudioRecord(MediaRecorder.AudioSource.VOICE_RECOGNITION, RATE, AudioFormat.CHANNEL_IN_MONO,
                AudioFormat.ENCODING_PCM_16BIT, max(minBuf, RATE / 5 * 2))
        } catch (e: Exception) { return false }
        if (rec.state != AudioRecord.STATE_INITIALIZED) { rec.release(); return false }

        val ns = if (noiseSuppress && NoiseSuppressor.isAvailable())
            try { NoiseSuppressor.create(rec.audioSessionId)?.apply { enabled = true } } catch (e: Exception) { null }
        else null

        try { rec.startRecording() } catch (e: Exception) { ns?.release(); rec.release(); return false }
        running = true
        thread = Thread({ loop(rec, ns) }, "mic-booster").apply { start() }
        return true
    }

    fun stop() {
        running = false
        thread?.join(500)
        thread = null
        detach()
        synchronized(lock) { preroll.clear() }
    }

    /** Подключить вход распознавателя: сначала отдаём «предзапись», дальше — живой звук */
    fun attach(stream: OutputStream) = synchronized(lock) {
        closeOut()
        sessionPeak = 0f
        try { for (b in preroll) stream.write(b) } catch (e: Exception) {}
        out = stream
    }

    fun detach() = synchronized(lock) { closeOut() }

    private fun closeOut() {
        try { out?.close() } catch (e: Exception) {}
        out = null
    }

    private fun loop(rec: AudioRecord, ns: NoiseSuppressor?) {
        val frame = ShortArray(FRAME)
        var g = gain
        var n = 0
        try {
            while (running) {
                val read = rec.read(frame, 0, FRAME)
                if (read <= 0) continue

                var peak = 1
                var sum = 0.0
                for (i in 0 until read) {
                    val v = abs(frame[i].toInt()); if (v > peak) peak = v
                    sum += v.toDouble() * v
                }
                // Ограничитель: мгновенно убавляем, если будет перегруз; плавно возвращаем усиление
                val target = min(gain, LIMIT / peak)
                g = if (target < g) target else g + (target - g) * 0.03f

                val bytes = ByteArray(read * 2)
                for (i in 0 until read) {
                    val s = (frame[i] * g).toInt().coerceIn(-32768, 32767)
                    bytes[2 * i] = (s and 0xff).toByte()
                    bytes[2 * i + 1] = (s shr 8 and 0xff).toByte()
                }
                val level = (sqrt(sum / read) * g / 32768.0).toFloat()
                if (level > sessionPeak) sessionPeak = level

                synchronized(lock) {
                    preroll.addLast(bytes); if (preroll.size > PREROLL_FRAMES) preroll.removeFirst()
                    out?.let { try { it.write(bytes) } catch (e: Exception) { closeOut() } }
                }
                if (++n % 5 == 0) onLevel(level)
            }
        } finally {
            try { rec.stop() } catch (e: Exception) {}
            ns?.release()
            rec.release()
            onLevel(0f)
        }
    }

    companion object {
        const val RATE = 16000
        private const val FRAME = 320           // 20 мс
        private const val PREROLL_FRAMES = 20   // 0,4 с
        private const val LIMIT = 29000f
    }
}
