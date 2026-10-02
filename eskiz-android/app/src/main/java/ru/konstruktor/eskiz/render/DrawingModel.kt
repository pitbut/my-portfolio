package ru.konstruktor.eskiz.render

import ru.konstruktor.eskiz.data.Project
import ru.konstruktor.eskiz.geom.Calibration
import ru.konstruktor.eskiz.geom.Circle
import ru.konstruktor.eskiz.geom.P
import ru.konstruktor.eskiz.geom.dist
import ru.konstruktor.eskiz.geom.Arc
import ru.konstruktor.eskiz.geom.circleThrough
import ru.konstruktor.eskiz.geom.fitCircle
import kotlin.math.PI
import kotlin.math.max
import kotlin.math.min
import java.util.Locale

/** Форматирование размера: до 0,1 мм, без лишнего «.0». */
fun fmtMm(v: Double): String {
    val s = String.format(Locale.US, "%.1f", v)
    return if (s.endsWith(".0")) s.dropLast(2) else s
}

/** Значения всех размеров проекта: введённые и вычисленные по калибровке. */
class Values(val project: Project, val cal: Calibration) {
    fun dim(id: Int): Double? {
        val d = project.dims.firstOrNull { it.id == id } ?: return null
        d.known?.let { return it }
        return computedDim(id)
    }

    fun computedDim(id: Int): Double? {
        if (!cal.calibrated) return null
        val d = project.dims.firstOrNull { it.id == id } ?: return null
        val a = project.point(d.a) ?: return null
        val b = project.point(d.b) ?: return null
        return dist(cal.toMm(a.p), cal.toMm(b.p))
    }

    fun dimUncertainty(id: Int): Double? {
        val d = project.dims.firstOrNull { it.id == id } ?: return null
        val a = project.point(d.a) ?: return null
        val b = project.point(d.b) ?: return null
        if (!cal.calibrated) return null
        return cal.uncertainty(a.p, b.p)
    }

    fun circleUncertainty(id: Int): Double? {
        val c = project.circles.firstOrNull { it.id == id } ?: return null
        return cal.circleUncertainty(c.pts)
    }

    fun circle(id: Int): Double? {
        val c = project.circles.firstOrNull { it.id == id } ?: return null
        c.known?.let { return it }
        return computedCircle(id)
    }

    fun computedCircle(id: Int): Double? {
        if (!cal.calibrated) return null
        val c = project.circles.firstOrNull { it.id == id } ?: return null
        return fitCircle(c.pts.map { cal.toMm(it) })?.r?.times(2)
    }

    fun arc(id: Int): Double? {
        val a = project.arcs.firstOrNull { it.id == id } ?: return null
        a.known?.let { return it }
        return computedArc(id)
    }

    fun computedArc(id: Int): Double? {
        if (!cal.calibrated) return null
        val a = project.arcs.firstOrNull { it.id == id } ?: return null
        val pa = project.point(a.a) ?: return null
        val pm = project.point(a.m) ?: return null
        val pb = project.point(a.b) ?: return null
        return circleThrough(cal.toMm(pa.p), cal.toMm(pm.p), cal.toMm(pb.p))?.r
    }

    fun arcUncertainty(id: Int): Double? {
        val a = project.arcs.firstOrNull { it.id == id } ?: return null
        val pts = listOfNotNull(project.point(a.a)?.p, project.point(a.m)?.p, project.point(a.b)?.p)
        if (pts.size < 3) return null
        return cal.circleUncertainty(pts)?.div(2)
    }
}

/**
 * Чертёж в мм: геометрия, приведённая калибровкой к плоскости детали и повёрнутая так,
 * чтобы самая длинная линия контура была горизонтальной (плюс ручной поворот по 90°).
 */
class DrawingModel(val project: Project, val cal: Calibration) {
    val values = Values(project, cal)
    val rotation: Double = run {
        val segs = project.lines.mapNotNull { l ->
            val a = project.point(l.a) ?: return@mapNotNull null
            val b = project.point(l.b) ?: return@mapNotNull null
            cal.toMm(a.p) to cal.toMm(b.p)
        }.ifEmpty {
            project.dims.mapNotNull { d ->
                val a = project.point(d.a) ?: return@mapNotNull null
                val b = project.point(d.b) ?: return@mapNotNull null
                cal.toMm(a.p) to cal.toMm(b.p)
            }
        }
        val longest = segs.maxByOrNull { dist(it.first, it.second) }
        var ang = if (longest == null) 0.0 else -(longest.second - longest.first).angle()
        // Минимальный поворот: приводим к диапазону (-45°, 45°].
        while (ang > PI / 4) ang -= PI / 2
        while (ang <= -PI / 4) ang += PI / 2
        ang + project.rotationSteps * PI / 2
    }

    fun map(imgP: P): P = cal.toMm(imgP).rotate(rotation)

    val lines: List<Pair<P, P>> = project.lines.mapNotNull { l ->
        val a = project.point(l.a) ?: return@mapNotNull null
        val b = project.point(l.b) ?: return@mapNotNull null
        map(a.p) to map(b.p)
    }

    class CircleItem(val id: Int, val circle: Circle, val value: Double?)

    val circles: List<CircleItem> = project.circles.mapNotNull { c ->
        val fc = fitCircle(c.pts.map { map(it) }) ?: return@mapNotNull null
        CircleItem(c.id, fc, values.circle(c.id))
    }

    class DimItem(val id: Int, val a: P, val b: P, val value: Double?)

    class ArcItem(val id: Int, val arc: Arc, val value: Double?)

    /** Дуги контура в мм чертежа. */
    val arcs: List<ArcItem> = project.arcs.mapNotNull { a ->
        val pa = project.point(a.a) ?: return@mapNotNull null
        val pm = project.point(a.m) ?: return@mapNotNull null
        val pb = project.point(a.b) ?: return@mapNotNull null
        val arc = Arc.through(map(pa.p), map(pm.p), map(pb.p)) ?: return@mapNotNull null
        ArcItem(a.id, arc, values.arc(a.id))
    }

    /**
     * Показывать ли размер на чертеже. Автоматически — размеры вдоль контура и горизонтальные/
     * вертикальные; диагонали, введённые для калибровки, на чертёж не выносятся.
     */
    fun shown(d: ru.konstruktor.eskiz.data.SDim): Boolean {
        d.onDrawing?.let { return it }
        if (project.lines.isEmpty()) return true
        if (project.lines.any { (it.a == d.a && it.b == d.b) || (it.a == d.b && it.b == d.a) }) return true
        val a = project.point(d.a) ?: return false
        val b = project.point(d.b) ?: return false
        val v = map(b.p) - map(a.p)
        val ang = Math.toDegrees(kotlin.math.atan2(kotlin.math.abs(v.y), kotlin.math.abs(v.x)))
        return ang < 2.0 || ang > 88.0
    }

    val dims: List<DimItem> = project.dims.filter(::shown).mapNotNull { d ->
        val a = project.point(d.a) ?: return@mapNotNull null
        val b = project.point(d.b) ?: return@mapNotNull null
        DimItem(d.id, map(a.p), map(b.p), values.dim(d.id))
    }

    /** Габарит геометрии [minX, minY, maxX, maxY]. */
    val bounds: DoubleArray = run {
        val pts = lines.flatMap { listOf(it.first, it.second) } + dims.flatMap { listOf(it.a, it.b) } +
            circles.flatMap { listOf(it.circle.c - P(it.circle.r, it.circle.r), it.circle.c + P(it.circle.r, it.circle.r)) } +
            arcs.flatMap { it.arc.sample(16) }
        if (pts.isEmpty()) doubleArrayOf(0.0, 0.0, 100.0, 100.0)
        else doubleArrayOf(pts.minOf { it.x }, pts.minOf { it.y }, pts.maxOf { it.x }, pts.maxOf { it.y })
    }

    /** Порядок появления размеров (для пошагового режима): id линейных и диаметральных размеров. */
    val revealOrder: List<Int> = (project.dims.map { it.id } + project.circles.map { it.id } + project.arcs.map { it.id }).sorted()
}

/** Масштабы по ГОСТ 2.302: отношение «лист / натура». */
private val SCALES = listOf(10.0, 5.0, 4.0, 2.5, 2.0, 1.0, 1 / 2.0, 1 / 2.5, 1 / 4.0, 1 / 5.0, 1 / 10.0, 1 / 15.0,
    1 / 20.0, 1 / 25.0, 1 / 40.0, 1 / 50.0, 1 / 75.0, 1 / 100.0, 1 / 200.0, 1 / 500.0, 1 / 1000.0)

fun scaleLabel(m: Double): String =
    if (m >= 1) "${fmtMm(m)}:1" else "1:${fmtMm(1 / m)}"

/** Раскладка листа: формат A4, ориентация и масштаб, при котором чертёж помещается. */
class PageSpec(val w: Double, val h: Double, val scale: Double) {
    // Рамка по ГОСТ 2.301: слева 20 мм, остальные 5 мм; внизу штамп 30 мм.
    val frameL = 20.0; val frameO = 5.0
    val stampW = 185.0; val stampH = 30.0
    /** Центр поля чертежа на листе. */
    val drawCenter = P((frameL + w - frameO) / 2, (frameO + h - frameO - stampH) / 2)

    companion object {
        private const val DIM_MARGIN = 22.0

        fun choose(bounds: DoubleArray): PageSpec {
            val bw = max(1e-6, bounds[2] - bounds[0])
            val bh = max(1e-6, bounds[3] - bounds[1])
            fun fit(w: Double, h: Double): Double {
                val aw = w - 20 - 5 - 2 * DIM_MARGIN
                val ah = h - 10 - 30 - 2 * DIM_MARGIN
                val maxM = min(aw / bw, ah / bh)
                return SCALES.firstOrNull { it <= maxM * 1.0001 } ?: SCALES.last()
            }
            val land = fit(297.0, 210.0)
            val port = fit(210.0, 297.0)
            return if (land >= port) PageSpec(297.0, 210.0, land) else PageSpec(210.0, 297.0, port)
        }
    }
}
