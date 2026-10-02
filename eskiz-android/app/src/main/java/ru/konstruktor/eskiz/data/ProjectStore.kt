package ru.konstruktor.eskiz.data

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Matrix
import android.net.Uri
import androidx.exifinterface.media.ExifInterface
import kotlinx.serialization.json.Json
import java.io.File
import java.util.UUID
import kotlin.math.max

/** Проекты хранятся в памяти телефона: projects/<id>/{photo.jpg, thumb.jpg, project.json}. */
class ProjectStore(private val context: Context) {
    private val json = Json { ignoreUnknownKeys = true; encodeDefaults = true }
    private val root = File(context.filesDir, "projects").apply { mkdirs() }

    fun dir(id: String) = File(root, id)
    fun photo(id: String) = File(dir(id), "photo.jpg")
    fun thumb(id: String) = File(dir(id), "thumb.jpg")

    fun list(): List<Project> = root.listFiles().orEmpty()
        .mapNotNull { d -> runCatching { load(d.name) }.getOrNull() }
        .sortedByDescending { it.updated }

    fun load(id: String): Project = json.decodeFromString(File(dir(id), "project.json").readText())

    fun save(p: Project) {
        val f = File(dir(p.id), "project.json")
        val tmp = File(dir(p.id), "project.json.tmp")
        tmp.writeText(json.encodeToString(Project.serializer(), p))
        tmp.renameTo(f)
    }

    fun delete(id: String) { dir(id).deleteRecursively() }

    /** Создаёт проект из фото: поворачивает по EXIF, ограничивает размер, делает миниатюру. */
    fun create(uri: Uri, name: String): Project {
        val bmp = decodeOriented(uri, MAX_SIDE) ?: error("Не удалось открыть фото")
        val id = UUID.randomUUID().toString()
        dir(id).mkdirs()
        photo(id).outputStream().use { bmp.compress(Bitmap.CompressFormat.JPEG, 93, it) }
        val ts = 400.0 / max(bmp.width, bmp.height)
        val th = Bitmap.createScaledBitmap(bmp, (bmp.width * ts).toInt().coerceAtLeast(1), (bmp.height * ts).toInt().coerceAtLeast(1), true)
        thumb(id).outputStream().use { th.compress(Bitmap.CompressFormat.JPEG, 85, it) }
        val now = System.currentTimeMillis()
        val p = Project(id = id, name = name, created = now, updated = now, imageW = bmp.width, imageH = bmp.height)
        bmp.recycle(); th.recycle()
        save(p)
        return p
    }

    private fun decodeOriented(uri: Uri, maxSide: Int): Bitmap? {
        val cr = context.contentResolver
        val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        cr.openInputStream(uri)?.use { BitmapFactory.decodeStream(it, null, bounds) }
        if (bounds.outWidth <= 0) return null
        var sample = 1
        while (max(bounds.outWidth, bounds.outHeight) / (sample * 2) >= maxSide) sample *= 2
        val raw = cr.openInputStream(uri)?.use {
            BitmapFactory.decodeStream(it, null, BitmapFactory.Options().apply { inSampleSize = sample })
        } ?: return null
        val orientation = cr.openInputStream(uri)?.use {
            ExifInterface(it).getAttributeInt(ExifInterface.TAG_ORIENTATION, ExifInterface.ORIENTATION_NORMAL)
        } ?: ExifInterface.ORIENTATION_NORMAL
        val m = Matrix()
        when (orientation) {
            ExifInterface.ORIENTATION_ROTATE_90 -> m.postRotate(90f)
            ExifInterface.ORIENTATION_ROTATE_180 -> m.postRotate(180f)
            ExifInterface.ORIENTATION_ROTATE_270 -> m.postRotate(270f)
            ExifInterface.ORIENTATION_FLIP_HORIZONTAL -> m.postScale(-1f, 1f)
            ExifInterface.ORIENTATION_FLIP_VERTICAL -> m.postScale(1f, -1f)
            ExifInterface.ORIENTATION_TRANSPOSE -> { m.postRotate(90f); m.postScale(-1f, 1f) }
            ExifInterface.ORIENTATION_TRANSVERSE -> { m.postRotate(270f); m.postScale(-1f, 1f) }
        }
        val maxNow = max(raw.width, raw.height)
        if (maxNow > maxSide) { val s = maxSide.toFloat() / maxNow; m.preScale(s, s) }
        if (m.isIdentity) return raw
        val out = Bitmap.createBitmap(raw, 0, 0, raw.width, raw.height, m, true)
        if (out !== raw) raw.recycle()
        return out
    }

    companion object {
        const val MAX_SIDE = 4000
    }
}
