package com.robutpit.screentranslator

import android.annotation.SuppressLint
import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Rect
import android.graphics.RectF
import android.text.Layout
import android.text.StaticLayout
import android.text.TextPaint
import android.view.View

/** Слой поверх экрана: рисует плашки с переводом прямо на месте исходного текста. */
@SuppressLint("ViewConstructor")
class OverlayView(context: Context) : View(context) {

    private class Block(val bg: RectF, val layout: StaticLayout, val x: Float, val y: Float)

    private val density = resources.displayMetrics.density
    private val scaled = resources.displayMetrics.scaledDensity
    private val bgPaint = Paint(Paint.ANTI_ALIAS_FLAG)
    private val textPaint = TextPaint(Paint.ANTI_ALIAS_FLAG)
    private var blocks: List<Block> = emptyList()
    private val loc = IntArray(2)

    var dark = true
    var textScale = 1f

    fun show(items: List<Pair<Rect, String>>) {
        bgPaint.color = if (dark) Color.argb(240, 28, 31, 36) else Color.argb(245, 255, 253, 240)
        textPaint.color = if (dark) Color.WHITE else Color.rgb(20, 20, 20)
        val screenH = resources.displayMetrics.heightPixels.toFloat() * 2
        blocks = items.map { (r, text) -> build(r, text, screenH) }
        invalidate()
    }

    fun clear() {
        if (blocks.isEmpty()) return
        blocks = emptyList()
        invalidate()
    }

    val isShowing get() = blocks.isNotEmpty()

    private fun build(r: Rect, text: String, maxBottom: Float): Block {
        val pad = 3 * density
        val width = (r.width() - 2 * pad).toInt().coerceAtLeast((40 * density).toInt())
        val maxH = r.height() - 2 * pad
        val maxSize = 16f * scaled * textScale
        val minSize = 9f * scaled * textScale

        // Подбираем размер шрифта так, чтобы перевод поместился в рамку оригинала.
        var size = maxSize.coerceAtMost((r.height() * 0.75f).coerceAtLeast(minSize))
        var layout: StaticLayout
        while (true) {
            textPaint.textSize = size
            layout = makeLayout(text, width)
            if (layout.height <= maxH || size <= minSize) break
            size = (size * 0.9f).coerceAtLeast(minSize)
        }
        var lineW = 0f
        for (i in 0 until layout.lineCount) lineW = maxOf(lineW, layout.getLineWidth(i))
        // Узкие элементы (кнопки, подписи) закрываем целиком; у широких (сообщения во всю ширину,
        // как в Telegram) плашка по ширине самого перевода, чтобы не затемнять пустое место.
        val screenW = resources.displayMetrics.widthPixels
        val coverW = if (r.width() < screenW * 0.6f) r.width().toFloat() else 0f
        val bg = RectF(
            r.left.toFloat(),
            r.top.toFloat(),
            r.left + maxOf(lineW + 2 * pad, coverW),
            maxOf(r.bottom.toFloat(), r.top + layout.height + 2 * pad).coerceAtMost(maxBottom)
        )
        val y = if (layout.height < r.height()) r.top + (r.height() - layout.height) / 2f else r.top + pad
        return Block(bg, layout, r.left + pad, y)
    }

    @Suppress("DEPRECATION")
    private fun makeLayout(text: String, width: Int): StaticLayout =
        if (android.os.Build.VERSION.SDK_INT >= 23) {
            StaticLayout.Builder.obtain(text, 0, text.length, TextPaint(textPaint), width)
                .setAlignment(Layout.Alignment.ALIGN_NORMAL)
                .setIncludePad(false)
                .build()
        } else {
            StaticLayout(text, TextPaint(textPaint), width, Layout.Alignment.ALIGN_NORMAL, 1f, 0f, false)
        }

    override fun onDraw(canvas: Canvas) {
        if (blocks.isEmpty()) return
        // Координаты узлов — экранные; учитываем, где на экране начинается наше окно.
        getLocationOnScreen(loc)
        canvas.save()
        canvas.translate(-loc[0].toFloat(), -loc[1].toFloat())
        val radius = 4 * density
        for (b in blocks) {
            canvas.drawRoundRect(b.bg, radius, radius, bgPaint)
            canvas.save()
            canvas.translate(b.x, b.y)
            b.layout.draw(canvas)
            canvas.restore()
        }
        canvas.restore()
    }
}
