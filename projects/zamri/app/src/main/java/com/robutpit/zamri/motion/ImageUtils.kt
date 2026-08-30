package com.robutpit.zamri.motion

import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Matrix
import android.graphics.Paint
import android.graphics.RectF
import android.graphics.YuvImage
import android.graphics.ImageFormat
import android.graphics.Rect as AndroidRect
import androidx.camera.core.ImageProxy
import java.io.ByteArrayOutputStream

object ImageUtils {

    /** Converts a YUV_420_888 [ImageProxy] frame into an upright RGB [Bitmap]. */
    fun imageProxyToBitmap(image: ImageProxy): Bitmap {
        val nv21 = yuv420ToNv21(image)
        val yuvImage = YuvImage(nv21, ImageFormat.NV21, image.width, image.height, null)
        val out = ByteArrayOutputStream()
        yuvImage.compressToJpeg(AndroidRect(0, 0, image.width, image.height), 95, out)
        val bytes = out.toByteArray()
        val bitmap = android.graphics.BitmapFactory.decodeByteArray(bytes, 0, bytes.size)

        val rotation = image.imageInfo.rotationDegrees
        if (rotation == 0) return bitmap
        val matrix = Matrix().apply { postRotate(rotation.toFloat()) }
        return Bitmap.createBitmap(bitmap, 0, 0, bitmap.width, bitmap.height, matrix, true)
    }

    private fun yuv420ToNv21(image: ImageProxy): ByteArray {
        val yPlane = image.planes[0]
        val uPlane = image.planes[1]
        val vPlane = image.planes[2]

        val ySize = yPlane.buffer.remaining()
        val uSize = uPlane.buffer.remaining()
        val vSize = vPlane.buffer.remaining()
        val nv21 = ByteArray(ySize + uSize + vSize)

        yPlane.buffer.get(nv21, 0, ySize)

        // Interleave V and U (NV21 = Y then V,U pairs). CameraX typically hands
        // back semi-planar planes with matching row/pixel strides on Camera2,
        // so a plain copy is correct for the common case; a full generic
        // stride-aware interleave is not needed for the fixed pixelStride=2
        // layout virtually every device reports for the analysis use case.
        val vBuffer = vPlane.buffer
        val uBuffer = uPlane.buffer
        var pos = ySize
        val chunk = ByteArray(1)
        if (vPlane.pixelStride == 2 && uPlane.pixelStride == 2) {
            vBuffer.get(nv21, pos, vSize)
            pos += vSize
            // uBuffer already interleaved with V at odd offsets in most NV12/21
            // semi-planar layouts; fall back to explicit interleave otherwise.
        } else {
            val vBytes = ByteArray(vSize).also { vBuffer.get(it) }
            val uBytes = ByteArray(uSize).also { uBuffer.get(it) }
            var i = 0
            var o = pos
            while (i < vBytes.size && i < uBytes.size && o + 1 < nv21.size) {
                nv21[o] = vBytes[i]
                nv21[o + 1] = uBytes[i]
                o += 2
                i++
            }
        }
        return nv21
    }

    /** Draws a red bounding box with a diagonal cross over the violation area, in-place. */
    fun markViolation(bitmap: Bitmap, boxFraction: RectF, label: String): Bitmap {
        val marked = bitmap.copy(Bitmap.Config.ARGB_8888, true)
        val canvas = Canvas(marked)
        val w = marked.width.toFloat()
        val h = marked.height.toFloat()
        val box = AndroidRect(
            (boxFraction.left * w).toInt().coerceIn(0, marked.width),
            (boxFraction.top * h).toInt().coerceIn(0, marked.height),
            (boxFraction.right * w).toInt().coerceIn(0, marked.width),
            (boxFraction.bottom * h).toInt().coerceIn(0, marked.height)
        )

        val strokePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.RED
            style = Paint.Style.STROKE
            strokeWidth = w * 0.01f
        }
        canvas.drawRect(box, strokePaint)
        canvas.drawLine(
            box.left.toFloat(), box.top.toFloat(),
            box.right.toFloat(), box.bottom.toFloat(), strokePaint
        )
        canvas.drawLine(
            box.right.toFloat(), box.top.toFloat(),
            box.left.toFloat(), box.bottom.toFloat(), strokePaint
        )

        val textPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.WHITE
            textSize = w * 0.045f
            setShadowLayer(6f, 0f, 0f, Color.BLACK)
        }
        val textBgPaint = Paint().apply { color = Color.argb(180, 200, 0, 0) }
        val textY = (box.top - h * 0.02f).coerceAtLeast(textPaint.textSize)
        val textWidth = textPaint.measureText(label)
        canvas.drawRect(
            box.left.toFloat(),
            textY - textPaint.textSize,
            box.left + textWidth + 16f,
            textY + 8f,
            textBgPaint
        )
        canvas.drawText(label, box.left + 8f, textY, textPaint)

        return marked
    }
}
