package com.robutpit.screentranslator

import android.accessibilityservice.AccessibilityService
import android.graphics.Bitmap
import android.os.Build
import android.view.Display
import androidx.annotation.RequiresApi
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.text.TextRecognition
import com.google.mlkit.vision.text.TextRecognizer
import com.google.mlkit.vision.text.chinese.ChineseTextRecognizerOptions
import com.google.mlkit.vision.text.japanese.JapaneseTextRecognizerOptions
import com.google.mlkit.vision.text.korean.KoreanTextRecognizerOptions
import com.google.mlkit.vision.text.latin.TextRecognizerOptions
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.tasks.await
import kotlin.coroutines.resume

/**
 * Запасной режим: снимок экрана средствами службы спец. возможностей (Android 11+,
 * без отдельного запроса на запись экрана) + распознавание текста ML Kit.
 * Нужен для текста внутри картинок, видео и игр, где обычного текста нет.
 */
class OcrScanner {

    sealed class Result {
        class Ok(val items: List<TextItem>) : Result()
        /** Окно защищено от снимков (FLAG_SECURE): так система защищает, например, банки. */
        object Secure : Result()
        object TooFrequent : Result()
        object Unsupported : Result()
        object Failed : Result()
    }

    private var recognizer: TextRecognizer? = null
    private var script: String? = null

    private fun recognizer(s: String): TextRecognizer {
        if (s != script) {
            recognizer?.close()
            recognizer = TextRecognition.getClient(
                when (s) {
                    "chinese" -> ChineseTextRecognizerOptions.Builder().build()
                    "japanese" -> JapaneseTextRecognizerOptions.Builder().build()
                    "korean" -> KoreanTextRecognizerOptions.Builder().build()
                    else -> TextRecognizerOptions.DEFAULT_OPTIONS
                }
            )
            script = s
        }
        return recognizer!!
    }

    suspend fun scan(service: AccessibilityService, ocrScript: String): Result {
        if (Build.VERSION.SDK_INT < 30) return Result.Unsupported
        val bmp = when (val shot = screenshot(service)) {
            is Shot.Ok -> shot.bitmap
            is Shot.Err -> return when (shot.code) {
                AccessibilityService.ERROR_TAKE_SCREENSHOT_INTERVAL_TIME_SHORT -> Result.TooFrequent
                SECURE_WINDOW -> Result.Secure
                else -> Result.Failed
            }
        }
        return try {
            val text = recognizer(ocrScript).process(InputImage.fromBitmap(bmp, 0)).await()
            val items = text.textBlocks.mapNotNull { b ->
                val box = b.boundingBox ?: return@mapNotNull null
                val t = b.lines.joinToString(" ") { it.text }.replace("- ", "").trim()
                if (t.count { it.isLetter() } < 2) null else TextItem(t, box)
            }
            // Полностью чёрный снимок = защищённое окно на старых версиях Android.
            if (items.isEmpty() && isBlack(bmp)) Result.Secure else Result.Ok(items)
        } catch (e: Exception) {
            Result.Failed
        } finally {
            bmp.recycle()
        }
    }

    private sealed class Shot {
        class Ok(val bitmap: Bitmap) : Shot()
        class Err(val code: Int) : Shot()
    }

    @RequiresApi(30)
    private suspend fun screenshot(service: AccessibilityService): Shot =
        suspendCancellableCoroutine { cont ->
            service.takeScreenshot(
                Display.DEFAULT_DISPLAY, service.mainExecutor,
                object : AccessibilityService.TakeScreenshotCallback {
                    override fun onSuccess(result: AccessibilityService.ScreenshotResult) {
                        val hb = result.hardwareBuffer
                        val bmp = Bitmap.wrapHardwareBuffer(hb, result.colorSpace)
                            ?.copy(Bitmap.Config.ARGB_8888, false)
                        hb.close()
                        cont.resume(if (bmp != null) Shot.Ok(bmp) else Shot.Err(-1))
                    }

                    override fun onFailure(errorCode: Int) {
                        cont.resume(Shot.Err(errorCode))
                    }
                })
        }

    private fun isBlack(b: Bitmap): Boolean {
        val stepX = maxOf(1, b.width / 24)
        val stepY = maxOf(1, b.height / 48)
        var y = 0
        while (y < b.height) {
            var x = 0
            while (x < b.width) {
                val c = b.getPixel(x, y)
                if ((c shr 16 and 0xff) + (c shr 8 and 0xff) + (c and 0xff) > 30) return false
                x += stepX
            }
            y += stepY
        }
        return true
    }

    fun close() {
        recognizer?.close()
    }

    private companion object {
        // AccessibilityService.ERROR_TAKE_SCREENSHOT_SECURE_WINDOW (API 34)
        const val SECURE_WINDOW = 5
    }
}
