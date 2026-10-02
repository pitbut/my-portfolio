package ru.konstruktor.eskiz.render

import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Path
import android.graphics.Typeface
import ru.konstruktor.eskiz.data.Project
import ru.konstruktor.eskiz.geom.Calibration
import ru.konstruktor.eskiz.geom.DimLayout
import ru.konstruktor.eskiz.geom.P
import ru.konstruktor.eskiz.geom.dist
import ru.konstruktor.eskiz.geom.fitCircle
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

object Colors {
    const val CONTOUR = 0xFFFFC107.toInt()
    const val KNOWN = 0xFF43A047.toInt()
    const val COMPUTED = 0xFF1E88E5.toInt()
    const val OUTLIER = 0xFFE53935.toInt()
    const val SELECTED = 0xFFFF6D00.toInt()
    const val INK = 0xFF000000.toInt()
}

object Renderer {
    private val gostFont: Typeface = Typeface.create(Typeface.SANS_SERIF, Typeface.ITALIC)

    class DimStyle(
        val textSize: Float,
        val lineW: Float,
        val arrow: Float,
        /** Белая подложка под линиями и текстом (для фото). */
        val halo: Boolean,
    ) {
        val textPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            textSize = this@DimStyle.textSize
            typeface = gostFont
            textAlign = Paint.Align.CENTER
        }
        /** Высота текста для раскладки (высота прописных букв). */
        val textH get() = textSize * 0.75

        fun params(gapMul: Double = 2.6, stepMul: Double = 2.1) = DimLayout.Params(
            textH = textH.toDouble(),
            gap = textH * gapMul,
            step = textH * stepMul,
            arrow = arrow.toDouble(),
            measure = { textPaint.measureText(it).toDouble() },
        )
    }

    // Экран и экспорт рисуют из разных потоков — у каждого потока свои кисти.
    private val strokeTL = ThreadLocal.withInitial {
        Paint(Paint.ANTI_ALIAS_FLAG).apply { style = Paint.Style.STROKE; strokeCap = Paint.Cap.ROUND; strokeJoin = Paint.Join.ROUND }
    }
    private val fillTL = ThreadLocal.withInitial { Paint(Paint.ANTI_ALIAS_FLAG).apply { style = Paint.Style.FILL } }
    private val stroke: Paint get() = strokeTL.get()!!
    private val fill: Paint get() = fillTL.get()!!

    private fun line(c: Canvas, a: P, b: P, color: Int, w: Float) {
        stroke.color = color; stroke.strokeWidth = w
        c.drawLine(a.x.toFloat(), a.y.toFloat(), b.x.toFloat(), b.y.toFloat(), stroke)
    }

    private fun haloLine(c: Canvas, a: P, b: P, color: Int, w: Float, halo: Boolean) {
        if (halo) line(c, a, b, Color.WHITE, w * 2.6f)
        line(c, a, b, color, w)
    }

    private fun arrow(c: Canvas, tip: P, dir: P, len: Float, color: Int, halo: Boolean) {
        // dir — направление от острия к хвосту
        val d = dir.norm()
        val n = d.perp()
        val base = tip + d * len.toDouble()
        val p = Path().apply {
            moveTo(tip.x.toFloat(), tip.y.toFloat())
            val l = base + n * (len / 6.0); val r = base - n * (len / 6.0)
            lineTo(l.x.toFloat(), l.y.toFloat()); lineTo(r.x.toFloat(), r.y.toFloat()); close()
        }
        if (halo) { stroke.color = Color.WHITE; stroke.strokeWidth = len / 4; c.drawPath(p, stroke) }
        fill.color = color
        c.drawPath(p, fill)
    }

    private fun text(c: Canvas, s: String, center: P, angleRad: Double, style: DimStyle, color: Int) {
        val tp = style.textPaint
        c.save()
        c.rotate(Math.toDegrees(angleRad).toFloat(), center.x.toFloat(), center.y.toFloat())
        val baseline = (center.y + style.textH / 2).toFloat()
        if (style.halo) {
            tp.style = Paint.Style.STROKE; tp.strokeWidth = style.textSize * 0.28f; tp.color = Color.WHITE
            tp.strokeJoin = Paint.Join.ROUND
            c.drawText(s, center.x.toFloat(), baseline, tp)
        }
        tp.style = Paint.Style.FILL; tp.color = color
        c.drawText(s, center.x.toFloat(), baseline, tp)
        c.restore()
    }

    /** Рисует разложенные размеры. */
    fun drawDims(c: Canvas, r: DimLayout.Result, style: DimStyle, colorOf: (Int) -> Int) {
        val w = style.lineW
        val over = style.textH * 0.5
        for (d in r.linear) {
            val col = colorOf(d.id)
            val u = (d.db - d.da).norm()
            // Выносные линии с выходом за размерную.
            for ((p, q) in listOf(d.a to d.da, d.b to d.db)) {
                val dir = q - p
                if (dir.len() > 1e-6) haloLine(c, p, q + dir.norm() * over, col, w, style.halo)
            }
            val len = dist(d.da, d.db)
            val tw = style.textPaint.measureText(d.text)
            val tProj = (d.textCenter - d.da).dot(u) + tw / 2
            val start = if (d.arrowsOutside) d.da - u * (style.arrow * 2.0) else d.da
            val end = if (tProj > len) d.da + u * (tProj + style.textH * 0.3) else if (d.arrowsOutside) d.db + u * (style.arrow * 2.0) else d.db
            haloLine(c, start, end, col, w, style.halo)
            if (d.arrowsOutside) {
                arrow(c, d.da, -u, style.arrow, col, style.halo)
                arrow(c, d.db, u, style.arrow, col, style.halo)
            } else {
                arrow(c, d.da, u, style.arrow, col, style.halo)
                arrow(c, d.db, -u, style.arrow, col, style.halo)
            }
            text(c, d.text, d.textCenter, d.textAngle, style, col)
        }
        for (d in r.diameters) {
            val col = colorOf(d.id)
            haloLine(c, d.start, d.elbow, col, w, style.halo)
            haloLine(c, d.elbow, d.shelfEnd, col, w, style.halo)
            arrow(c, d.start, d.elbow - d.start, style.arrow, col, style.halo)
            text(c, d.text, d.textCenter, 0.0, style, col)
        }
    }

    class PhotoOverlay(
        val selectedDim: Int? = null,
        val selectedPoint: Int? = null,
        val selectedLine: Int? = null,
        val selectedCircle: Int? = null,
        val pendingPoints: Set<Int> = emptySet(),
        val pendingCirclePts: List<P> = emptyList(),
        val showDims: Boolean = true,
        val showLines: Boolean = true,
        /** null — показывать все размеры, иначе только эти id (пошаговый режим). */
        val visible: Set<Int>? = null,
    )

    /**
     * Разметка поверх фото. [toScreen] переводит пиксели фото в пиксели экрана.
     * Возвращает раскладку размеров (в координатах экрана) — для выбора размера касанием.
     */
    fun drawPhotoOverlay(
        c: Canvas, project: Project, cal: Calibration, toScreen: (P) -> P, dp: Float, o: PhotoOverlay,
    ): DimLayout.Result {
        val values = Values(project, cal)
        val segs = if (o.showLines) project.lines.mapNotNull { l ->
            val a = project.point(l.a) ?: return@mapNotNull null
            val b = project.point(l.b) ?: return@mapNotNull null
            Triple(l.id, toScreen(a.p), toScreen(b.p))
        } else emptyList()
        for ((id, a, b) in segs) {
            line(c, a, b, 0x99000000.toInt(), 4.5f * dp)
            line(c, a, b, if (id == o.selectedLine) Colors.SELECTED else Colors.CONTOUR, 2.2f * dp)
        }

        // Окружности: рисуем как замкнутую кривую через точки края (на фото это эллипсы).
        val circlesScreen = project.circles.mapNotNull { ci ->
            val pts = ci.pts.map(toScreen)
            val fc = fitCircle(pts) ?: return@mapNotNull null
            val path = Path()
            pts.forEachIndexed { i, p -> if (i == 0) path.moveTo(p.x.toFloat(), p.y.toFloat()) else path.lineTo(p.x.toFloat(), p.y.toFloat()) }
            if (pts.size >= 6) path.close() else {
                path.reset(); path.addCircle(fc.c.x.toFloat(), fc.c.y.toFloat(), fc.r.toFloat(), Path.Direction.CW)
            }
            stroke.color = 0x99000000.toInt(); stroke.strokeWidth = 4.5f * dp; c.drawPath(path, stroke)
            stroke.color = if (ci.id == o.selectedCircle) Colors.SELECTED else Colors.CONTOUR; stroke.strokeWidth = 2.2f * dp
            c.drawPath(path, stroke)
            Triple(ci, fc, values)
        }

        val style = DimStyle(textSize = 15f * dp, lineW = 1.4f * dp, arrow = 9f * dp, halo = true)
        val lin = if (o.showDims) project.dims.filter { o.visible == null || it.id in o.visible }.mapNotNull { d ->
            val a = project.point(d.a) ?: return@mapNotNull null
            val b = project.point(d.b) ?: return@mapNotNull null
            val txt = when {
                d.known != null -> fmtMm(d.known) + if (d.id in cal.outliers) " ⚠" else ""
                else -> values.computedDim(d.id)?.let { v ->
                    // Большую погрешность показываем сразу — это сигнал добавить размеры.
                    val u = cal.uncertainty(a.p, b.p) ?: 0.0
                    "≈" + fmtMm(v) + if (u > maxOf(0.5, v * 0.015)) " ±" + fmtMm(u) else ""
                } ?: "?"
            }
            DimLayout.LinearIn(d.id, toScreen(a.p), toScreen(b.p), txt)
        } else emptyList()
        val dia = if (o.showDims) circlesScreen.filter { o.visible == null || it.first.id in o.visible }.map { (ci, fc, v) ->
            val txt = when {
                ci.known != null -> "Ø" + fmtMm(ci.known) + if (ci.id in cal.outliers) " ⚠" else ""
                else -> v.computedCircle(ci.id)?.let { "Ø≈" + fmtMm(it) } ?: "Ø?"
            }
            DimLayout.DiameterIn(ci.id, fc.c, fc.r, txt)
        } else emptyList()
        val layout = DimLayout.layout(segs.map { it.second to it.third }, circlesScreen.map { it.second }, lin, dia, style.params())
        drawDims(c, layout, style) { id ->
            val known = project.dims.firstOrNull { it.id == id }?.known ?: project.circles.firstOrNull { it.id == id }?.known
            when {
                id == o.selectedDim -> Colors.SELECTED
                id in cal.outliers -> Colors.OUTLIER
                known != null -> Colors.KNOWN
                else -> Colors.COMPUTED
            }
        }

        // Точки.
        for (p in project.points) {
            val s = toScreen(p.p)
            val hi = p.id == o.selectedPoint || p.id in o.pendingPoints
            val r = (if (hi) 7f else 4.5f) * dp
            fill.color = 0xCC000000.toInt(); c.drawCircle(s.x.toFloat(), s.y.toFloat(), r + 1.5f * dp, fill)
            fill.color = if (hi) Colors.SELECTED else Color.WHITE; c.drawCircle(s.x.toFloat(), s.y.toFloat(), r, fill)
        }
        for (p in o.pendingCirclePts) {
            val s = toScreen(p)
            fill.color = Colors.SELECTED; c.drawCircle(s.x.toFloat(), s.y.toFloat(), 5f * dp, fill)
        }
        return layout
    }

    /**
     * Лист чертежа. [k] — пикселей холста на 1 мм листа, ([ox], [oy]) — положение угла листа на холсте.
     */
    fun drawPage(
        c: Canvas, model: DrawingModel, page: PageSpec, k: Float, ox: Float, oy: Float,
        visible: Set<Int>? = null,
    ) {
        fun paper(x: Double, y: Double) = P(ox + x * k, oy + y * k)
        fill.color = Color.WHITE
        c.drawRect(ox, oy, ox + page.w.toFloat() * k, oy + page.h.toFloat() * k, fill)

        val thick = 0.6f * k
        val thin = 0.25f * k
        // Рамка.
        val fl = page.frameL; val fo = page.frameO
        val corners = listOf(paper(fl, fo), paper(page.w - fo, fo), paper(page.w - fo, page.h - fo), paper(fl, page.h - fo))
        for (i in 0..3) line(c, corners[i], corners[(i + 1) % 4], Colors.INK, thick)

        // Модель → лист.
        val b = model.bounds
        val mc = P((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
        val m = page.scale
        fun mp(p: P): P { val q = page.drawCenter + (p - mc) * m; return paper(q.x, q.y) }

        val segs = model.lines.map { mp(it.first) to mp(it.second) }
        for ((a, bb) in segs) line(c, a, bb, Colors.INK, thick)
        val circles = model.circles.map { ci -> ci to ru.konstruktor.eskiz.geom.Circle(mp(ci.circle.c), ci.circle.r * m * k) }
        for ((_, cc) in circles) {
            stroke.color = Colors.INK; stroke.strokeWidth = thick
            c.drawCircle(cc.c.x.toFloat(), cc.c.y.toFloat(), cc.r.toFloat(), stroke)
            // Осевые линии отверстия.
            val ext = cc.r + 2.0 * k
            dashed(c, cc.c - P(ext, 0.0), cc.c + P(ext, 0.0), thin, k)
            dashed(c, cc.c - P(0.0, ext), cc.c + P(0.0, ext), thin, k)
        }

        val style = DimStyle(textSize = 4.7f * k, lineW = thin, arrow = 3f * k, halo = false)
        val p = DimLayout.Params(style.textH.toDouble(), 10.0 * k, 7.0 * k, style.arrow.toDouble()) { style.textPaint.measureText(it).toDouble() }
        val lin = model.dims.filter { visible == null || it.id in visible }
            .map { DimLayout.LinearIn(it.id, mp(it.a), mp(it.b), it.value?.let(::fmtMm) ?: "?") }
        val dia = circles.filter { visible == null || it.first.id in visible }
            .map { (ci, cc) -> DimLayout.DiameterIn(ci.id, cc.c, cc.r, "Ø" + (ci.value?.let(::fmtMm) ?: "?")) }
        val layout = DimLayout.layout(segs, circles.map { it.second }, lin, dia, p)
        drawDims(c, layout, style) { Colors.INK }

        drawStamp(c, model, page, k, ox, oy)
    }

    private fun dashed(c: Canvas, a: P, b: P, w: Float, k: Float) {
        val len = dist(a, b)
        val u = (b - a).norm()
        var t = 0.0
        var dash = true
        while (t < len) {
            val seg = if (dash) 6.0 * k else 1.5 * k
            if (dash) line(c, a + u * t, a + u * minOf(len, t + seg), Colors.INK, w)
            t += seg; dash = !dash
        }
    }

    private fun drawStamp(c: Canvas, model: DrawingModel, page: PageSpec, k: Float, ox: Float, oy: Float) {
        val x0 = page.w - page.frameO - page.stampW
        val y0 = page.h - page.frameO - page.stampH
        fun pt(x: Double, y: Double) = P(ox + (x0 + x) * k, oy + (y0 + y) * k)
        val thick = 0.6f * k; val thin = 0.25f * k
        val W = page.stampW; val H = page.stampH
        line(c, pt(0.0, 0.0), pt(W, 0.0), Colors.INK, thick)
        line(c, pt(0.0, 0.0), pt(0.0, H), Colors.INK, thick)
        // Колонки: подписи 0–65 | наименование 65–135 | масштаб/лист 135–185.
        line(c, pt(65.0, 0.0), pt(65.0, H), Colors.INK, thick)
        line(c, pt(135.0, 0.0), pt(135.0, H), Colors.INK, thick)
        for (y in listOf(10.0, 20.0)) {
            line(c, pt(0.0, y), pt(65.0, y), Colors.INK, thin)
            line(c, pt(135.0, y), pt(W, y), Colors.INK, thin)
        }
        line(c, pt(22.0, 0.0), pt(22.0, H), Colors.INK, thin)
        line(c, pt(50.0, 0.0), pt(50.0, H), Colors.INK, thin)
        line(c, pt(160.0, 0.0), pt(160.0, H), Colors.INK, thin)

        val tp = Paint(Paint.ANTI_ALIAS_FLAG).apply { typeface = gostFont; color = Colors.INK; textAlign = Paint.Align.LEFT }
        fun t(s: String, x: Double, y: Double, size: Double, center: Boolean = false) {
            tp.textSize = (size * k).toFloat()
            tp.textAlign = if (center) Paint.Align.CENTER else Paint.Align.LEFT
            val q = pt(x, y)
            c.drawText(s, q.x.toFloat(), q.y.toFloat(), tp)
        }
        val st = model.project.stamp
        val date = SimpleDateFormat("dd.MM.yy", Locale("ru")).format(Date(model.project.updated))
        t("Разраб.", 1.5, 6.8, 2.8); t(st.author.take(14), 23.0, 6.8, 2.8); t(date, 51.0, 6.8, 2.5)
        t("Пров.", 1.5, 16.8, 2.8)
        t("Утв.", 1.5, 26.8, 2.8)
        val title = st.title.ifBlank { model.project.name }
        t(title.take(26), 100.0, 13.0, if (title.length > 16) 3.5 else 5.0, center = true)
        if (st.material.isNotBlank()) t(st.material.take(30), 100.0, 25.0, 2.8, center = true)
        t("Масштаб", 136.5, 6.8, 2.8); t(if (model.cal.calibrated) scaleLabel(page.scale) else "б/м", 161.5, 6.8, 3.2)
        t("Лист", 136.5, 16.8, 2.8); t("1", 161.5, 16.8, 3.2)
        t("Листов", 136.5, 26.8, 2.8); t("1", 161.5, 26.8, 3.2)
    }
}
