package ru.rynok.app.media

import android.content.Context
import android.media.MediaPlayer
import android.media.MediaRecorder
import android.os.Build
import java.io.File

/** Запись и воспроизведение голосовых сообщений чата (формат AAC/M4A). */
class AudioRecorderManager(private val context: Context) {

    private var recorder: MediaRecorder? = null
    private var player: MediaPlayer? = null
    private var recordStartedAt: Long = 0L

    fun startRecording(outputFile: File): Boolean {
        return try {
            @Suppress("DEPRECATION")
            val mediaRecorder = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                MediaRecorder(context)
            } else {
                MediaRecorder()
            }
            mediaRecorder.apply {
                setAudioSource(MediaRecorder.AudioSource.MIC)
                setOutputFormat(MediaRecorder.OutputFormat.MPEG_4)
                setAudioEncoder(MediaRecorder.AudioEncoder.AAC)
                setOutputFile(outputFile.absolutePath)
                prepare()
                start()
            }
            recorder = mediaRecorder
            recordStartedAt = System.currentTimeMillis()
            true
        } catch (e: Exception) {
            recorder = null
            false
        }
    }

    /** @return длительность записи в мс, либо null если запись не была начата успешно. */
    fun stopRecording(): Long? {
        val current = recorder ?: return null
        return try {
            current.stop()
            System.currentTimeMillis() - recordStartedAt
        } catch (e: Exception) {
            null
        } finally {
            current.release()
            recorder = null
        }
    }

    fun cancelRecording() {
        try {
            recorder?.stop()
        } catch (_: Exception) {
        }
        recorder?.release()
        recorder = null
    }

    fun play(file: File, onCompletion: () -> Unit = {}) {
        stopPlayback()
        player = MediaPlayer().apply {
            setDataSource(file.absolutePath)
            setOnCompletionListener { onCompletion(); stopPlayback() }
            prepare()
            start()
        }
    }

    fun stopPlayback() {
        player?.let {
            try {
                if (it.isPlaying) it.stop()
            } catch (_: Exception) {
            }
            it.release()
        }
        player = null
    }
}
