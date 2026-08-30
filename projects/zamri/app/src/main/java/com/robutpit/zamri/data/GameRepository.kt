package com.robutpit.zamri.data

import android.content.ContentValues
import android.content.Context
import android.graphics.Bitmap
import android.os.Environment
import android.provider.MediaStore
import com.robutpit.zamri.data.db.ViolationDao
import com.robutpit.zamri.data.db.ViolationEntity
import com.robutpit.zamri.data.db.ViolationSide
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.withContext
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * Persists violation snapshots: the JPEG goes to MediaStore
 * (Pictures/DollGame, visible in the system gallery) while its metadata
 * (round, sector, side, timestamp) is mirrored into Room for the in-app
 * archive screen.
 */
class GameRepository(
    private val context: Context,
    private val dao: ViolationDao
) {

    fun observeAll(): Flow<List<ViolationEntity>> = dao.observeAll()

    fun observeByRound(round: Int): Flow<List<ViolationEntity>> = dao.observeByRound(round)

    suspend fun clearArchive() = dao.clearAll()

    suspend fun saveViolation(
        bitmap: Bitmap,
        round: Int,
        lane: Int,
        sideLane: Int,
        side: ViolationSide,
        motionScore: Float
    ): ViolationEntity = withContext(Dispatchers.IO) {
        val now = System.currentTimeMillis()
        val fileName = "violation_${FILE_TIME_FORMAT.format(Date(now))}_r${round}_l${lane}.jpg"
        val uri = insertIntoMediaStore(fileName, now)

        context.contentResolver.openOutputStream(uri)?.use { out ->
            bitmap.compress(Bitmap.CompressFormat.JPEG, 92, out)
        } ?: error("Unable to open MediaStore output stream for $uri")

        val entity = ViolationEntity(
            timestampMillis = now,
            round = round,
            lane = lane,
            sideLane = sideLane,
            side = side,
            photoUri = uri.toString(),
            motionScore = motionScore
        )
        val id = dao.insert(entity)
        entity.copy(id = id)
    }

    private fun insertIntoMediaStore(fileName: String, timestampMillis: Long) = run {
        val values = ContentValues().apply {
            put(MediaStore.Images.Media.DISPLAY_NAME, fileName)
            put(MediaStore.Images.Media.MIME_TYPE, "image/jpeg")
            put(MediaStore.Images.Media.DATE_ADDED, timestampMillis / 1000)
            put(
                MediaStore.Images.Media.RELATIVE_PATH,
                Environment.DIRECTORY_PICTURES + "/" + ALBUM_NAME
            )
        }
        context.contentResolver.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, values)
            ?: error("MediaStore refused to create a new entry")
    }

    companion object {
        private const val ALBUM_NAME = "DollGame"
        private val FILE_TIME_FORMAT =
            SimpleDateFormat("yyyyMMdd_HHmmss_SSS", Locale.US)
    }
}
