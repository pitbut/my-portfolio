package ru.rynok.app.media

import android.content.Context
import android.net.Uri
import androidx.core.content.FileProvider
import java.io.File
import java.util.UUID

object MediaFiles {

    private fun mediaDir(context: Context): File =
        File(context.cacheDir, "media").apply { mkdirs() }

    fun newVoiceFile(context: Context): File =
        File(mediaDir(context), "voice_${UUID.randomUUID()}.m4a")

    fun newVideoFile(context: Context): File =
        File(mediaDir(context), "video_${UUID.randomUUID()}.mp4")

    fun uriFor(context: Context, file: File): Uri =
        FileProvider.getUriForFile(context, "${context.packageName}.fileprovider", file)
}
