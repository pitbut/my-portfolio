package com.robutpit.zamri.motion

import android.graphics.RectF
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageProxy
import kotlin.math.max
import kotlin.math.min

/** One sector that crossed the movement threshold on a single analyzed frame. */
data class SectorTrigger(
    val label: SectorLabel,
    /** Fraction (0..1) of changed pixels inside this sector, post-morphology. */
    val changedRatio: Float,
    /** Bounding box of the changed pixels, as fractions of the full frame. */
    val boxFraction: RectF
)

/**
 * CameraX [ImageAnalysis.Analyzer] that finds motion via grayscale frame
 * differencing: abs(current - previous) per pixel, threshold to a binary
 * mask, a light erode+dilate pass to drop single-pixel sensor noise, then a
 * changed-pixel ratio per vertical sector. Cheap enough to run every frame
 * on-device without any ML model.
 *
 * Only does work while [armed] is true (i.e. during the red-light phase) -
 * green-light frames are dropped immediately to save battery.
 */
class MotionDetector(
    private var sectorCount: Int,
    private var sensitivityPercent: Int,
    private val onTrigger: (List<SectorTrigger>, ImageProxy) -> Unit
) : ImageAnalysis.Analyzer {

    @Volatile
    var armed: Boolean = false

    private var previousGray: ByteArray? = null
    private var gridW = 0
    private var gridH = 0

    fun updateSectorCount(count: Int) {
        sectorCount = count
    }

    fun updateSensitivity(percent: Int) {
        sensitivityPercent = percent
    }

    /** Drops any stored previous frame so the next armed frame doesn't diff against a stale one. */
    fun resetBaseline() {
        previousGray = null
    }

    override fun analyze(image: ImageProxy) {
        if (!armed) {
            image.close()
            return
        }

        val (grid, w, h) = sampleRotatedGray(image, ANALYSIS_WIDTH)
        val previous = previousGray

        if (previous == null || previous.size != grid.size || gridW != w || gridH != h) {
            previousGray = grid
            gridW = w
            gridH = h
            image.close()
            return
        }

        val pixelThreshold = lerp(PIXEL_THRESHOLD_MAX, PIXEL_THRESHOLD_MIN, sensitivityPercent / 100f)
        val binary = ByteArray(grid.size)
        for (i in grid.indices) {
            val diff = kotlin.math.abs((grid[i].toInt() and 0xFF) - (previous[i].toInt() and 0xFF))
            binary[i] = if (diff > pixelThreshold) 1 else 0
        }

        val cleaned = dilate(erode(binary, w, h), w, h)

        val sectorRatioThreshold =
            lerp(SECTOR_RATIO_MAX, SECTOR_RATIO_MIN, sensitivityPercent / 100f)
        val triggers = mutableListOf<SectorTrigger>()
        val sectorWidth = w.toFloat() / sectorCount

        for (sector in 0 until sectorCount) {
            val xStart = (sector * sectorWidth).toInt().coerceIn(0, w)
            val xEnd = ((sector + 1) * sectorWidth).toInt().coerceIn(0, w)
            if (xEnd <= xStart) continue

            var changed = 0
            var minX = w
            var maxX = 0
            var minY = h
            var maxY = 0
            val total = (xEnd - xStart) * h

            for (y in 0 until h) {
                val rowOffset = y * w
                for (x in xStart until xEnd) {
                    if (cleaned[rowOffset + x].toInt() == 1) {
                        changed++
                        if (x < minX) minX = x
                        if (x > maxX) maxX = x
                        if (y < minY) minY = y
                        if (y > maxY) maxY = y
                    }
                }
            }

            val ratio = if (total > 0) changed.toFloat() / total else 0f
            if (ratio > sectorRatioThreshold && changed > MIN_CHANGED_PIXELS) {
                triggers += SectorTrigger(
                    label = labelForSector(sector, sectorCount),
                    changedRatio = ratio,
                    boxFraction = RectF(
                        minX.toFloat() / w,
                        minY.toFloat() / h,
                        (maxX + 1f) / w,
                        (maxY + 1f) / h
                    )
                )
            }
        }

        previousGray = grid
        gridW = w
        gridH = h

        if (triggers.isNotEmpty()) {
            onTrigger(triggers, image)
        } else {
            image.close()
        }
    }

    /** 3x3 "all neighbours set" pass - drops isolated noise pixels. */
    private fun erode(src: ByteArray, w: Int, h: Int): ByteArray {
        val out = ByteArray(src.size)
        for (y in 0 until h) {
            for (x in 0 until w) {
                val idx = y * w + x
                if (src[idx].toInt() == 0) continue
                var allSet = true
                for (dy in -1..1) {
                    for (dx in -1..1) {
                        val ny = y + dy
                        val nx = x + dx
                        if (nx < 0 || nx >= w || ny < 0 || ny >= h) continue
                        if (src[ny * w + nx].toInt() == 0) {
                            allSet = false
                        }
                    }
                }
                out[idx] = if (allSet) 1 else 0
            }
        }
        return out
    }

    /** 3x3 "any neighbour set" pass - regrows the surviving blobs back to size. */
    private fun dilate(src: ByteArray, w: Int, h: Int): ByteArray {
        val out = ByteArray(src.size)
        for (y in 0 until h) {
            for (x in 0 until w) {
                val idx = y * w + x
                var anySet = src[idx].toInt() == 1
                if (!anySet) {
                    outer@ for (dy in -1..1) {
                        for (dx in -1..1) {
                            val ny = y + dy
                            val nx = x + dx
                            if (nx < 0 || nx >= w || ny < 0 || ny >= h) continue
                            if (src[ny * w + nx].toInt() == 1) {
                                anySet = true
                                break@outer
                            }
                        }
                    }
                }
                out[idx] = if (anySet) 1 else 0
            }
        }
        return out
    }

    /**
     * Samples the Y (luma) plane down to roughly [targetWidth] px wide,
     * pre-rotated to upright orientation so grid column 0 always maps to the
     * frame's own left edge regardless of how the sensor is mounted.
     */
    private fun sampleRotatedGray(image: ImageProxy, targetWidth: Int): Triple<ByteArray, Int, Int> {
        val plane = image.planes[0]
        val buffer = plane.buffer
        val rowStride = plane.rowStride
        val pixelStride = plane.pixelStride
        val srcW = image.width
        val srcH = image.height
        val rotation = image.imageInfo.rotationDegrees

        val rotatedW = if (rotation == 90 || rotation == 270) srcH else srcW
        val rotatedH = if (rotation == 90 || rotation == 270) srcW else srcH

        val scale = max(1, rotatedW / targetWidth)
        val dstW = max(1, rotatedW / scale)
        val dstH = max(1, rotatedH / scale)

        val out = ByteArray(dstW * dstH)
        for (dy in 0 until dstH) {
            val ry = min(rotatedH - 1, dy * scale)
            for (dx in 0 until dstW) {
                val rx = min(rotatedW - 1, dx * scale)
                val (sx, sy) = rotatedToSource(rx, ry, srcW, srcH, rotation)
                val offset = sy * rowStride + sx * pixelStride
                out[dy * dstW + dx] = if (offset in 0 until buffer.capacity()) buffer[offset] else 0
            }
        }
        return Triple(out, dstW, dstH)
    }

    /** Maps a coordinate in the upright (rotated) grid back to the raw sensor buffer. */
    private fun rotatedToSource(
        rx: Int, ry: Int,
        srcW: Int, srcH: Int,
        rotation: Int
    ): Pair<Int, Int> = when (rotation) {
        0 -> rx to ry
        90 -> ry to (srcH - 1 - rx)
        180 -> (srcW - 1 - rx) to (srcH - 1 - ry)
        270 -> (srcW - 1 - ry) to rx
        else -> rx to ry
    }

    companion object {
        private const val ANALYSIS_WIDTH = 160
        private const val PIXEL_THRESHOLD_MIN = 8
        private const val PIXEL_THRESHOLD_MAX = 45
        private const val SECTOR_RATIO_MIN = 0.015f
        private const val SECTOR_RATIO_MAX = 0.12f
        private const val MIN_CHANGED_PIXELS = 12

        private fun lerp(a: Float, b: Float, t: Float) = a + (b - a) * t.coerceIn(0f, 1f)
        private fun lerp(a: Int, b: Int, t: Float) = lerp(a.toFloat(), b.toFloat(), t).toInt()
    }
}
