package ru.konstruktor.eskiz.geom3d

import ru.konstruktor.eskiz.export.Extrusion
import ru.konstruktor.eskiz.geom.P
import ru.konstruktor.eskiz.render.fmtMm
import kotlin.math.abs
import kotlin.math.acos
import kotlin.math.ceil
import kotlin.math.max

/**
 * 3D по нескольким видам. Контур каждого вида выдавливается в направлении взгляда,
 * деталь — общая часть этих тел; отверстия и вырезы вида — сквозные по этому направлению.
 *
 * Оси: X — вправо, Y — от смотрящего спереди (вглубь), Z — вверх.
 */
object MultiView {

    enum class Role(val title: String, val axisA: Int, val signA: Double, val axisB: Int, val axisT: Int) {
        /** Спереди: смотрим вдоль +Y, на чертеже вправо — X, вверх — Z. */
        FRONT("Спереди", 0, 1.0, 2, 1),
        /** Сверху: смотрим вниз, вправо — X, вверх по чертежу — Y (от нас). */
        TOP("Сверху", 0, 1.0, 1, 2),
        /** Слева: смотрим вдоль +X, вправо — −Y, вверх — Z. */
        LEFT("Слева", 1, -1.0, 2, 0),
        /** Справа: смотрим вдоль −X, вправо — +Y, вверх — Z. */
        RIGHT("Справа", 1, 1.0, 2, 0),
    }

    class View(val role: Role, val profile: Extrusion.Profile, val mirror: Boolean = false)

    class Result(val solid: Solid, val warnings: List<String>, val size: V3)

    class BuildError(message: String) : Exception(message)

    private val AXIS_NAME = listOf("ширина (X)", "глубина (Y)", "высота (Z)")
    private fun unitAxis(i: Int) = when (i) { 0 -> V3(1.0, 0.0, 0.0); 1 -> V3(0.0, 1.0, 0.0); else -> V3(0.0, 0.0, 1.0) }

    /** Контур в точки: дуги разбиваются так, чтобы отклонение хорды было не больше 0,02 мм. */
    fun polygon(loop: Extrusion.Loop): List<P> = loop.edges.flatMap { e ->
        when (e) {
            is Extrusion.Edge2.Line -> listOf(e.p)
            is Extrusion.Edge2.Circ -> {
                val tau = 2 * Math.PI
                val a0 = (e.p - e.c).angle(); val a1 = (e.q - e.c).angle()
                var sw = ((a1 - a0) % tau + tau) % tau
                if (!e.ccw) sw = tau - sw
                if (sw < 1e-9) sw = tau
                val step = 2 * acos((1 - 0.02 / e.r).coerceIn(-1.0, 1.0))
                val n = ceil(sw / max(step, 1e-3)).toInt().coerceIn(4, 128)
                e.sample(n).dropLast(1)
            }
        }
    }

    fun build(views: List<View>, thickness: Double? = null): Result {
        if (views.isEmpty()) throw BuildError("Выберите хотя бы один вид")
        if (views.map { it.role }.distinct().size != views.size) throw BuildError("Каждый вид можно выбрать только один раз")
        val warnings = ArrayList<String>()

        class Prepared(val view: View, val sign: Double, val outer: List<P>, val inner: List<List<P>>) {
            val ra get() = outer.minOf { it.x } to outer.maxOf { it.x }
            val rb get() = outer.minOf { it.y } to outer.maxOf { it.y }
        }
        val prepared = views.map { v ->
            val sign = v.role.signA * (if (v.mirror) -1.0 else 1.0)
            fun tr(l: Extrusion.Loop) = polygon(l).map { P(it.x * sign, it.y) }
            Prepared(v, sign, tr(v.profile.outer), v.profile.inner.map(::tr))
        }

        // Диапазоны по мировым осям и согласование размеров между видами.
        val ranges = Array(3) { ArrayList<Pair<Prepared, Pair<Double, Double>>>() }
        for (p in prepared) {
            ranges[p.view.role.axisA] += p to p.ra
            ranges[p.view.role.axisB] += p to p.rb
        }
        // scale[view][axis] и смещение — приводим каждый вид к общему началу и длине.
        val target = DoubleArray(3)
        val single = views.size == 1
        for (axis in 0..2) {
            val r = ranges[axis]
            if (r.isEmpty()) {
                if (!single) throw BuildError("Не хватает вида: не задана ${AXIS_NAME[axis]}")
                target[axis] = thickness ?: throw BuildError("Для одного вида укажите толщину детали")
                continue
            }
            val lens = r.map { it.second.second - it.second.first }
            val avg = lens.average()
            val spread = (lens.max() - lens.min()) / avg
            target[axis] = avg
            if (r.size > 1 && spread > 0.03) {
                warnings += "Не совпадает ${AXIS_NAME[axis]}: " +
                    r.joinToString(", ") { (p, rr) -> "«${p.view.role.title}» ${fmtMm(rr.second - rr.first)} мм" } +
                    ". Проверьте размеры видов."
            }
        }
        fun mapA(p: Prepared, x: Double): Double {
            val (lo, hi) = p.ra
            val len = hi - lo
            val k = if (len > 0 && ranges[p.view.role.axisA].size > 1 && abs(target[p.view.role.axisA] / len - 1) <= 0.03)
                target[p.view.role.axisA] / len else 1.0
            return (x - lo) * k
        }
        fun mapB(p: Prepared, y: Double): Double {
            val (lo, hi) = p.rb
            val len = hi - lo
            val k = if (len > 0 && ranges[p.view.role.axisB].size > 1 && abs(target[p.view.role.axisB] / len - 1) <= 0.03)
                target[p.view.role.axisB] / len else 1.0
            return (y - lo) * k
        }

        val margin = 10.0
        val maxLen = target.max()
        var solid: List<Csg.Poly>? = null
        val cutters = ArrayList<List<Csg.Poly>>()
        for (p in prepared) {
            val role = p.view.role
            val (t0, t1) = if (single) 0.0 to target[role.axisT] else -margin to maxLen + margin
            val ea = unitAxis(role.axisA); val eb = unitAxis(role.axisB); val et = unitAxis(role.axisT)
            fun loopW(l: List<P>) = l.map { P(mapA(p, it.x), mapB(p, it.y)) }
            val body = prism(loopW(p.outer), t0, t1, ea, eb, et)
            solid = if (solid == null) body else Csg.intersect(solid, body)
            for (h in p.inner) cutters += prism(loopW(h), t0 - margin, t1 + margin, ea, eb, et)
        }
        var polys = solid!!
        for (c in cutters) polys = Csg.subtract(polys, c)
        if (polys.isEmpty()) throw BuildError("Виды не пересекаются — проверьте, что выбраны правильные стороны")

        val s = Solid.fromPolygons(polys)
        if (s.openEdges() > 0) warnings += "Модель получилась незамкнутой (${s.openEdges()} рёбер без пары) — STEP может открыться с ошибкой, STL обычно в порядке."
        val (lo, hi) = s.bounds
        return Result(s, warnings, V3(hi.x - lo.x, hi.y - lo.y, hi.z - lo.z))
    }
}
