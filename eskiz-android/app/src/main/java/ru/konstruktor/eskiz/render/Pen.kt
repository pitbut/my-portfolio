package ru.konstruktor.eskiz.render

import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Path
import android.graphics.RectF
import android.graphics.Typeface
import ru.konstruktor.eskiz.geom.Arc
import ru.konstruktor.eskiz.geom.P
import java.util.Locale
import kotlin.math.abs

/**
 * Примитивы рисования. Одна и та же отрисовка чертежа идёт на экран/PNG/PDF ([CanvasPen])
 * и в SVG ([SvgPen]), поэтому все форматы выглядят одинаково.
 */
interface Pen {
    fun line(a: P, b: P, color: Int, w: Float)
    fun polyline(pts: List<P>, closed: Boolean, color: Int, w: Float)
    fun fillPolygon(pts: List<P>, color: Int)
    fun circle(c: P, r: Double, color: Int, w: Float)
    fun arc(arc: Arc, color: Int, w: Float)
    fun fillRect(x0: Double, y0: Double, x1: Double, y1: Double, color: Int)
    fun fillCircle(c: P, r: Double, color: Int)

    /**
     * Текст: [at] — точка базовой линии (по центру или слева), [angleDeg] — поворот вокруг [pivot].
     * [halo] — ширина белой обводки (0 — без неё).
     */
    fun text(s: String, at: P, size: Float, color: Int, center: Boolean, angleDeg: Float = 0f, pivot: P = at, halo: Float = 0f)

    fun measure(s: String, size: Float): Float
}

val GOST_FONT: Typeface = Typeface.create(Typeface.SANS_SERIF, Typeface.ITALIC)

class CanvasPen(private val c: Canvas) : Pen {
    private val stroke = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE; strokeCap = Paint.Cap.ROUND; strokeJoin = Paint.Join.ROUND
    }
    private val fill = Paint(Paint.ANTI_ALIAS_FLAG).apply { style = Paint.Style.FILL }
    private val tp = Paint(Paint.ANTI_ALIAS_FLAG).apply { typeface = GOST_FONT }

    private fun s(color: Int, w: Float) = stroke.apply { this.color = color; strokeWidth = w }

    override fun line(a: P, b: P, color: Int, w: Float) =
        c.drawLine(a.x.toFloat(), a.y.toFloat(), b.x.toFloat(), b.y.toFloat(), s(color, w))

    private fun path(pts: List<P>, closed: Boolean) = Path().apply {
        pts.forEachIndexed { i, p -> if (i == 0) moveTo(p.x.toFloat(), p.y.toFloat()) else lineTo(p.x.toFloat(), p.y.toFloat()) }
        if (closed) close()
    }

    override fun polyline(pts: List<P>, closed: Boolean, color: Int, w: Float) {
        if (pts.size >= 2) c.drawPath(path(pts, closed), s(color, w))
    }

    override fun fillPolygon(pts: List<P>, color: Int) {
        fill.color = color
        c.drawPath(path(pts, true), fill)
    }

    override fun circle(c0: P, r: Double, color: Int, w: Float) =
        c.drawCircle(c0.x.toFloat(), c0.y.toFloat(), r.toFloat(), s(color, w))

    override fun arc(arc: Arc, color: Int, w: Float) {
        val oval = RectF((arc.c.x - arc.r).toFloat(), (arc.c.y - arc.r).toFloat(), (arc.c.x + arc.r).toFloat(), (arc.c.y + arc.r).toFloat())
        c.drawArc(oval, Math.toDegrees(arc.start).toFloat(), Math.toDegrees(arc.sweep).toFloat(), false, s(color, w))
    }

    override fun fillRect(x0: Double, y0: Double, x1: Double, y1: Double, color: Int) {
        fill.color = color
        c.drawRect(x0.toFloat(), y0.toFloat(), x1.toFloat(), y1.toFloat(), fill)
    }

    override fun fillCircle(c0: P, r: Double, color: Int) {
        fill.color = color
        c.drawCircle(c0.x.toFloat(), c0.y.toFloat(), r.toFloat(), fill)
    }

    override fun text(s: String, at: P, size: Float, color: Int, center: Boolean, angleDeg: Float, pivot: P, halo: Float) {
        tp.textSize = size
        tp.textAlign = if (center) Paint.Align.CENTER else Paint.Align.LEFT
        c.save()
        if (angleDeg != 0f) c.rotate(angleDeg, pivot.x.toFloat(), pivot.y.toFloat())
        if (halo > 0f) {
            tp.style = Paint.Style.STROKE; tp.strokeWidth = halo; tp.strokeJoin = Paint.Join.ROUND; tp.color = Color.WHITE
            c.drawText(s, at.x.toFloat(), at.y.toFloat(), tp)
        }
        tp.style = Paint.Style.FILL; tp.color = color
        c.drawText(s, at.x.toFloat(), at.y.toFloat(), tp)
        c.restore()
    }

    override fun measure(s: String, size: Float): Float { tp.textSize = size; return tp.measureText(s) }
}

/** SVG в тех же координатах, что и холст (единицы — мм листа при k = 1). */
class SvgPen(private val measurer: (String, Float) -> Float) : Pen {
    private val sb = StringBuilder()
    private fun f(v: Double) = String.format(Locale.US, "%.3f", v)
    private fun f(v: Float) = f(v.toDouble())
    private fun col(c: Int) = String.format("#%06X", c and 0xFFFFFF)
    private fun esc(s: String) = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    override fun line(a: P, b: P, color: Int, w: Float) {
        sb.append("<line x1=\"${f(a.x)}\" y1=\"${f(a.y)}\" x2=\"${f(b.x)}\" y2=\"${f(b.y)}\" stroke=\"${col(color)}\" stroke-width=\"${f(w)}\" stroke-linecap=\"round\"/>\n")
    }

    override fun polyline(pts: List<P>, closed: Boolean, color: Int, w: Float) {
        val tag = if (closed) "polygon" else "polyline"
        sb.append("<$tag points=\"${pts.joinToString(" ") { f(it.x) + "," + f(it.y) }}\" fill=\"none\" stroke=\"${col(color)}\" stroke-width=\"${f(w)}\" stroke-linejoin=\"round\"/>\n")
    }

    override fun fillPolygon(pts: List<P>, color: Int) {
        sb.append("<polygon points=\"${pts.joinToString(" ") { f(it.x) + "," + f(it.y) }}\" fill=\"${col(color)}\"/>\n")
    }

    override fun circle(c: P, r: Double, color: Int, w: Float) {
        sb.append("<circle cx=\"${f(c.x)}\" cy=\"${f(c.y)}\" r=\"${f(r)}\" fill=\"none\" stroke=\"${col(color)}\" stroke-width=\"${f(w)}\"/>\n")
    }

    override fun arc(arc: Arc, color: Int, w: Float) {
        val s = arc.at(0.0); val e = arc.at(1.0)
        val large = if (abs(arc.sweep) > Math.PI) 1 else 0
        val sweep = if (arc.sweep > 0) 1 else 0
        sb.append("<path d=\"M ${f(s.x)} ${f(s.y)} A ${f(arc.r)} ${f(arc.r)} 0 $large $sweep ${f(e.x)} ${f(e.y)}\" fill=\"none\" stroke=\"${col(color)}\" stroke-width=\"${f(w)}\"/>\n")
    }

    override fun fillRect(x0: Double, y0: Double, x1: Double, y1: Double, color: Int) {
        sb.append("<rect x=\"${f(x0)}\" y=\"${f(y0)}\" width=\"${f(x1 - x0)}\" height=\"${f(y1 - y0)}\" fill=\"${col(color)}\"/>\n")
    }

    override fun fillCircle(c: P, r: Double, color: Int) {
        sb.append("<circle cx=\"${f(c.x)}\" cy=\"${f(c.y)}\" r=\"${f(r)}\" fill=\"${col(color)}\"/>\n")
    }

    override fun text(s: String, at: P, size: Float, color: Int, center: Boolean, angleDeg: Float, pivot: P, halo: Float) {
        val tr = if (angleDeg != 0f) " transform=\"rotate(${f(angleDeg)} ${f(pivot.x)} ${f(pivot.y)})\"" else ""
        val anchor = if (center) "middle" else "start"
        val h = if (halo > 0f) " stroke=\"#FFFFFF\" stroke-width=\"${f(halo)}\" paint-order=\"stroke\"" else ""
        sb.append("<text x=\"${f(at.x)}\" y=\"${f(at.y)}\" font-family=\"sans-serif\" font-style=\"italic\" font-size=\"${f(size)}\" text-anchor=\"$anchor\" fill=\"${col(color)}\"$h$tr>${esc(s)}</text>\n")
    }

    override fun measure(s: String, size: Float) = measurer(s, size)

    fun document(widthMm: Double, heightMm: Double): String =
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n" +
            "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"${f(widthMm)}mm\" height=\"${f(heightMm)}mm\" viewBox=\"0 0 ${f(widthMm)} ${f(heightMm)}\">\n" +
            sb + "</svg>\n"
}
