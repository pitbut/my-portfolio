package ru.konstruktor.eskiz.render

import android.graphics.Color
import ru.konstruktor.eskiz.data.Project
import ru.konstruktor.eskiz.geom.Arc
import ru.konstruktor.eskiz.geom.Calibration
import ru.konstruktor.eskiz.geom.Circle
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

    class DimStyle(
        val pen: Pen,
        val textSize: Float,
        val lineW: Float,
        val arrow: Float,
        /** Белая подложка под линиями и текстом (для фото). */
        val halo: Boolean,
    ) {
        /** Высота текста для раскладки (высота прописных букв). */
        val textH get() = textSize * 0.75

        fun measure(s: String) = pen.measure(s, textSize)

        fun params(gapMul: Double = 2.6, stepMul: Double = 2.1) = DimLayout.Params(
            textH = textH.toDouble(),
            gap = textH * gapMul,
            step = textH * stepMul,
            arrow = arrow.toDouble(),
            measure = { measure(it).toDouble() },
        )
    }

    private fun haloLine(pen: Pen, a: P, b: P, color: Int, w: Float, halo: Boolean) {
        if (halo) pen.line(a, b, Color.WHITE, w * 2.6f)
        pen.line(a, b, color, w)
    }

    private fun arrow(pen: Pen, tip: P, dir: P, len: Float, color: Int, halo: Boolean) {
        // dir — направление от острия к хвосту
        val d = dir.norm()
        val n = d.perp()
        val base = tip + d * len.toDouble()
        val pts = listOf(tip, base + n * (len / 6.0), base - n * (len / 6.0))
        if (halo) pen.polyline(pts, true, Color.WHITE, len / 4)
        pen.fillPolygon(pts, color)
    }

    private fun text(s: String, center: P, angleRad: Double, style: DimStyle, color: Int) {
        val baseline = P(center.x, center.y + style.textH / 2)
        style.pen.text(
            s, baseline, style.textSize, color, center = true,
            angleDeg = Math.toDegrees(angleRad).toFloat(), pivot = center,
            halo = if (style.halo) style.textSize * 0.28f else 0f,
        )
    }

    /** Рисует разложенные размеры. */
    fun drawDims(r: DimLayout.Result, style: DimStyle, colorOf: (Int) -> Int) {
        val pen = style.pen
        val w = style.lineW
        val over = style.textH * 0.5
        for (d in r.linear) {
            val col = colorOf(d.id)
            val u = (d.db - d.da).norm()
            // Выносные линии с выходом за размерную.
            for ((p, q) in listOf(d.a to d.da, d.b to d.db)) {
                val dir = q - p
                if (dir.len() > 1e-6) haloLine(pen, p, q + dir.norm() * over, col, w, style.halo)
            }
            val len = dist(d.da, d.db)
            val tw = style.measure(d.text)
            val tProj = (d.textCenter - d.da).dot(u) + tw / 2
            val start = if (d.arrowsOutside) d.da - u * (style.arrow * 2.0) else d.da
            val end = if (tProj > len) d.da + u * (tProj + style.textH * 0.3) else if (d.arrowsOutside) d.db + u * (style.arrow * 2.0) else d.db
            haloLine(pen, start, end, col, w, style.halo)
            if (d.arrowsOutside) {
                arrow(pen, d.da, -u, style.arrow, col, style.halo)
                arrow(pen, d.db, u, style.arrow, col, style.halo)
            } else {
                arrow(pen, d.da, u, style.arrow, col, style.halo)
                arrow(pen, d.db, -u, style.arrow, col, style.halo)
            }
            text(d.text, d.textCenter, d.textAngle, style, col)
        }
        for (d in r.diameters) {
            val col = colorOf(d.id)
            haloLine(pen, d.start, d.elbow, col, w, style.halo)
            haloLine(pen, d.elbow, d.shelfEnd, col, w, style.halo)
            arrow(pen, d.start, d.elbow - d.start, style.arrow, col, style.halo)
            text(d.text, d.textCenter, 0.0, style, col)
        }
    }

    /** Допустимые направления выноски радиуса — внутри раствора дуги. */
    fun radiusAngles(a: Arc) = listOf(a.mid, a.mid - a.sweep * 0.3, a.mid + a.sweep * 0.3)

    class PhotoOverlay(
        val selectedDim: Int? = null,
        val selectedPoint: Int? = null,
        val selectedLine: Int? = null,
        val selectedCircle: Int? = null,
        val selectedArc: Int? = null,
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
        pen: Pen, project: Project, cal: Calibration, toScreen: (P) -> P, dp: Float, o: PhotoOverlay,
    ): DimLayout.Result {
        val values = Values(project, cal)
        val shadow = 0x99000000.toInt()
        val segs = if (o.showLines) project.lines.mapNotNull { l ->
            val a = project.point(l.a) ?: return@mapNotNull null
            val b = project.point(l.b) ?: return@mapNotNull null
            Triple(l.id, toScreen(a.p), toScreen(b.p))
        } else emptyList()
        for ((id, a, b) in segs) {
            pen.line(a, b, shadow, 4.5f * dp)
            pen.line(a, b, if (id == o.selectedLine) Colors.SELECTED else Colors.CONTOUR, 2.2f * dp)
        }

        // Дуги (на фото — по трём точкам в экранных координатах).
        val arcsScreen = if (o.showLines) project.arcs.mapNotNull { a ->
            val pa = project.point(a.a) ?: return@mapNotNull null
            val pm = project.point(a.m) ?: return@mapNotNull null
            val pb = project.point(a.b) ?: return@mapNotNull null
            a to Arc.through(toScreen(pa.p), toScreen(pm.p), toScreen(pb.p))
        } else emptyList()
        for ((a, arc) in arcsScreen) {
            val col = if (a.id == o.selectedArc) Colors.SELECTED else Colors.CONTOUR
            if (arc != null) { pen.arc(arc, shadow, 4.5f * dp); pen.arc(arc, col, 2.2f * dp) }
        }

        // Окружности: замкнутая кривая через точки края (на фото это эллипсы).
        val circlesScreen = project.circles.mapNotNull { ci ->
            val pts = ci.pts.map(toScreen)
            val fc = fitCircle(pts) ?: return@mapNotNull null
            val col = if (ci.id == o.selectedCircle) Colors.SELECTED else Colors.CONTOUR
            if (pts.size >= 6) { pen.polyline(pts, true, shadow, 4.5f * dp); pen.polyline(pts, true, col, 2.2f * dp) }
            else { pen.circle(fc.c, fc.r, shadow, 4.5f * dp); pen.circle(fc.c, fc.r, col, 2.2f * dp) }
            ci to fc
        }

        val style = DimStyle(pen, textSize = 15f * dp, lineW = 1.4f * dp, arrow = 9f * dp, halo = true)
        fun vis(id: Int) = o.showDims && (o.visible == null || id in o.visible)
        val lin = project.dims.filter { vis(it.id) }.mapNotNull { d ->
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
        }
        val dia = circlesScreen.filter { vis(it.first.id) }.map { (ci, fc) ->
            val txt = when {
                ci.known != null -> "Ø" + fmtMm(ci.known) + if (ci.id in cal.outliers) " ⚠" else ""
                else -> values.computedCircle(ci.id)?.let { "Ø≈" + fmtMm(it) } ?: "Ø?"
            }
            DimLayout.DiameterIn(ci.id, fc.c, fc.r, txt)
        } + arcsScreen.filter { vis(it.first.id) && it.second != null }.map { (a, arc) ->
            val txt = when {
                a.known != null -> "R" + fmtMm(a.known) + if (a.id in cal.outliers) " ⚠" else ""
                else -> values.computedArc(a.id)?.let { "R≈" + fmtMm(it) } ?: "R?"
            }
            DimLayout.DiameterIn(a.id, arc!!.c, arc.r, txt, radiusAngles(arc))
        }
        val geometry = segs.map { it.second to it.third } +
            arcsScreen.mapNotNull { it.second }.flatMap { it.sample(12).zipWithNext() }
        val layout = DimLayout.layout(geometry, circlesScreen.map { it.second }, lin, dia, style.params())
        drawDims(layout, style) { id ->
            val known = project.dims.firstOrNull { it.id == id }?.known
                ?: project.circles.firstOrNull { it.id == id }?.known
                ?: project.arcs.firstOrNull { it.id == id }?.known
            when {
                id == o.selectedDim || id == o.selectedArc || id == o.selectedCircle -> Colors.SELECTED
                id in cal.outliers -> Colors.OUTLIER
                known != null -> Colors.KNOWN
                else -> Colors.COMPUTED
            }
        }

        // Точки.
        for (p in project.points) {
            val s = toScreen(p.p)
            val hi = p.id == o.selectedPoint || p.id in o.pendingPoints
            val r = (if (hi) 7.0 else 4.5) * dp
            pen.fillCircle(s, r + 1.5 * dp, 0xCC000000.toInt())
            pen.fillCircle(s, r, if (hi) Colors.SELECTED else Color.WHITE)
        }
        for (p in o.pendingCirclePts) pen.fillCircle(toScreen(p), 5.0 * dp, Colors.SELECTED)
        return layout
    }

    /**
     * Лист чертежа. [k] — единиц холста на 1 мм листа, ([ox], [oy]) — положение угла листа на холсте.
     */
    fun drawPage(
        pen: Pen, model: DrawingModel, page: PageSpec, k: Float, ox: Float, oy: Float,
        visible: Set<Int>? = null,
    ) {
        fun paper(x: Double, y: Double) = P(ox + x * k, oy + y * k)
        pen.fillRect(ox.toDouble(), oy.toDouble(), ox + page.w * k, oy + page.h * k, Color.WHITE)

        val thick = 0.6f * k
        val thin = 0.25f * k
        // Рамка.
        val fl = page.frameL; val fo = page.frameO
        val corners = listOf(paper(fl, fo), paper(page.w - fo, fo), paper(page.w - fo, page.h - fo), paper(fl, page.h - fo))
        for (i in 0..3) pen.line(corners[i], corners[(i + 1) % 4], Colors.INK, thick)

        // Модель → лист.
        val b = model.bounds
        val mc = P((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
        val m = page.scale
        fun mp(p: P): P { val q = page.drawCenter + (p - mc) * m; return paper(q.x, q.y) }

        val segs = model.lines.map { mp(it.first) to mp(it.second) }
        for ((a, bb) in segs) pen.line(a, bb, Colors.INK, thick)
        // Поворот и масштаб сохраняют окружности, поэтому дуга на листе — та же дуга.
        val arcs = model.arcs.map { ai -> ai to Arc(mp(ai.arc.c), ai.arc.r * m * k, ai.arc.start, ai.arc.sweep) }
        for ((_, a) in arcs) pen.arc(a, Colors.INK, thick)
        val circles = model.circles.map { ci -> ci to Circle(mp(ci.circle.c), ci.circle.r * m * k) }
        for ((_, cc) in circles) {
            pen.circle(cc.c, cc.r, Colors.INK, thick)
            // Осевые линии отверстия.
            val ext = cc.r + 2.0 * k
            dashed(pen, cc.c - P(ext, 0.0), cc.c + P(ext, 0.0), thin, k)
            dashed(pen, cc.c - P(0.0, ext), cc.c + P(0.0, ext), thin, k)
        }

        val style = DimStyle(pen, textSize = 4.7f * k, lineW = thin, arrow = 3f * k, halo = false)
        val p = DimLayout.Params(style.textH.toDouble(), 10.0 * k, 7.0 * k, style.arrow.toDouble()) { style.measure(it).toDouble() }
        val lin = model.dims.filter { visible == null || it.id in visible }
            .map { DimLayout.LinearIn(it.id, mp(it.a), mp(it.b), it.value?.let(::fmtMm) ?: "?") }
        val dia = circles.filter { visible == null || it.first.id in visible }
            .map { (ci, cc) -> DimLayout.DiameterIn(ci.id, cc.c, cc.r, "Ø" + (ci.value?.let(::fmtMm) ?: "?")) } +
            arcs.filter { visible == null || it.first.id in visible }
                .map { (ai, a) -> DimLayout.DiameterIn(ai.id, a.c, a.r, "R" + (ai.value?.let(::fmtMm) ?: "?"), radiusAngles(a)) }
        val geometry = segs + arcs.flatMap { it.second.sample(12).zipWithNext() }
        val layout = DimLayout.layout(geometry, circles.map { it.second }, lin, dia, p)
        drawDims(layout, style) { Colors.INK }

        drawStamp(pen, model, page, k, ox, oy)
    }

    private fun dashed(pen: Pen, a: P, b: P, w: Float, k: Float) {
        val len = dist(a, b)
        val u = (b - a).norm()
        var t = 0.0
        var dash = true
        while (t < len) {
            val seg = if (dash) 6.0 * k else 1.5 * k
            if (dash) pen.line(a + u * t, a + u * minOf(len, t + seg), Colors.INK, w)
            t += seg; dash = !dash
        }
    }

    private fun drawStamp(pen: Pen, model: DrawingModel, page: PageSpec, k: Float, ox: Float, oy: Float) {
        val x0 = page.w - page.frameO - page.stampW
        val y0 = page.h - page.frameO - page.stampH
        fun pt(x: Double, y: Double) = P(ox + (x0 + x) * k, oy + (y0 + y) * k)
        val thick = 0.6f * k; val thin = 0.25f * k
        val w = page.stampW; val h = page.stampH
        pen.line(pt(0.0, 0.0), pt(w, 0.0), Colors.INK, thick)
        pen.line(pt(0.0, 0.0), pt(0.0, h), Colors.INK, thick)
        // Колонки: подписи 0–65 | наименование 65–135 | масштаб/лист 135–185.
        pen.line(pt(65.0, 0.0), pt(65.0, h), Colors.INK, thick)
        pen.line(pt(135.0, 0.0), pt(135.0, h), Colors.INK, thick)
        for (y in listOf(10.0, 20.0)) {
            pen.line(pt(0.0, y), pt(65.0, y), Colors.INK, thin)
            pen.line(pt(135.0, y), pt(w, y), Colors.INK, thin)
        }
        pen.line(pt(22.0, 0.0), pt(22.0, h), Colors.INK, thin)
        pen.line(pt(50.0, 0.0), pt(50.0, h), Colors.INK, thin)
        pen.line(pt(160.0, 0.0), pt(160.0, h), Colors.INK, thin)

        fun t(s: String, x: Double, y: Double, size: Double, center: Boolean = false) =
            pen.text(s, pt(x, y), (size * k).toFloat(), Colors.INK, center)
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
