package ru.konstruktor.eskiz.geom

import kotlin.math.PI
import kotlin.math.abs
import kotlin.math.cos
import kotlin.math.max
import kotlin.math.sin

/**
 * Автоматическая раскладка размеров без наложений.
 *
 * Все координаты — в единицах холста (пиксели экрана или мм листа), ось Y вниз.
 * Правила: размерная линия выносится за контур детали, короткие размеры ставятся ближе,
 * длинные дальше; при наложении размер переносится на следующий «этаж» или на другую сторону.
 */
object DimLayout {

    class LinearIn(val id: Int, val a: P, val b: P, val text: String)
    class DiameterIn(val id: Int, val c: P, val r: Double, val text: String)

    class Params(
        /** Высота шрифта размерного числа. */
        val textH: Double,
        /** Отступ первой размерной линии от контура. */
        val gap: Double,
        /** Шаг между параллельными размерными линиями. */
        val step: Double,
        /** Длина стрелки. */
        val arrow: Double,
        /** Ширина текста в тех же единицах. */
        val measure: (String) -> Double,
    )

    class LinearOut(
        val id: Int,
        val a: P, val b: P,
        /** Концы размерной линии. */
        val da: P, val db: P,
        val textCenter: P,
        /** Угол текста в радианах (всегда читаемый, в пределах ±90°). */
        val textAngle: Double,
        val text: String,
        /** Стрелки снаружи (размер короче двух стрелок). */
        val arrowsOutside: Boolean,
    )

    class DiameterOut(
        val id: Int,
        val c: P, val r: Double,
        /** Точка на окружности, где стоит стрелка. */
        val start: P,
        /** Излом выноски. */
        val elbow: P,
        /** Конец полки. */
        val shelfEnd: P,
        val textCenter: P,
        val text: String,
    )

    class Result(val linear: List<LinearOut>, val diameters: List<DiameterOut>)

    /** Повёрнутый прямоугольник для проверки пересечений. */
    class ORect(val c: P, val u: P, val hw: Double, val hh: Double) {
        private val v get() = u.perp()
        fun corners(): List<P> {
            val du = u * hw; val dv = v * hh
            return listOf(c + du + dv, c - du + dv, c - du - dv, c + du - dv)
        }

        fun intersects(o: ORect): Boolean {
            if (dist(c, o.c) > hw + hh + o.hw + o.hh) return false
            val ca = corners(); val cb = o.corners()
            for (axis in listOf(u, v, o.u, o.v)) {
                val (a0, a1) = project(ca, axis)
                val (b0, b1) = project(cb, axis)
                if (a1 < b0 || b1 < a0) return false
            }
            return true
        }

        private fun project(pts: List<P>, axis: P): Pair<Double, Double> {
            var lo = Double.MAX_VALUE; var hi = -Double.MAX_VALUE
            for (p in pts) { val d = p.dot(axis); if (d < lo) lo = d; if (d > hi) hi = d }
            return lo to hi
        }

        companion object {
            fun segment(a: P, b: P, halfThickness: Double) =
                ORect(lerp(a, b, 0.5), (b - a).norm(), dist(a, b) / 2, halfThickness)
        }
    }

    /** Направление, в котором текст читается слева направо (угол в пределах ±90°). */
    fun readable(u: P): P {
        var r = if (u.x < 0) -u else u
        // Почти вертикальный размер читается снизу вверх (ГОСТ 2.307).
        if (r.y > 0 && r.x < 0.035) r = -r
        return r
    }

    fun layout(
        geometry: List<Pair<P, P>>,
        circles: List<Circle>,
        linear: List<LinearIn>,
        diameters: List<DiameterIn>,
        p: Params,
    ): Result {
        val texts = ArrayList<ORect>()
        val dimLines = ArrayList<ORect>()
        val extLines = ArrayList<ORect>()
        val geomRects = geometry.filter { dist(it.first, it.second) > 1e-6 }
            .map { ORect.segment(it.first, it.second, p.textH * 0.05) } +
            circles.map { ORect(it.c, P(1.0, 0.0), it.r * 0.8, it.r * 0.8) }

        val allPts = geometry.flatMap { listOf(it.first, it.second) } + circles.map { it.c } +
            linear.flatMap { listOf(it.a, it.b) }
        val centroid = if (allPts.isEmpty()) P(0.0, 0.0)
        else P(allPts.sumOf { it.x } / allPts.size, allPts.sumOf { it.y } / allPts.size)

        val outLinear = ArrayList<LinearOut>()
        for (d in linear.sortedBy { dist(it.a, it.b) }) {
            val len = dist(d.a, d.b)
            if (len < 1e-6) continue
            val u = (d.b - d.a).norm()
            val n0 = u.perp()
            val mid = lerp(d.a, d.b, 0.5)
            val pref = if ((mid - centroid).dot(n0) >= 0) 1.0 else -1.0

            var best: Candidate? = null
            for (side in doubleArrayOf(pref, -pref)) {
                val n = n0 * side
                val ext = extent(d.a, u, len, n, geometry, circles)
                for (k in 0 until 12) {
                    val off = ext + p.gap + k * p.step
                    val cand = buildLinear(d, u, n, off, p)
                    if (texts.any { it.intersects(cand.textRect) } ||
                        dimLines.any { it.intersects(cand.textRect) } ||
                        extLines.any { it.intersects(cand.textRect) } ||
                        texts.any { it.intersects(cand.lineRect) } ||
                        dimLines.any { parallelOverlap(it, cand.lineRect) }
                    ) continue
                    val soft = geomRects.count { it.intersects(cand.textRect) } * 5 +
                        dimLines.count { it.intersects(cand.lineRect) } * 2 +
                        cand.extRects.sumOf { e -> texts.count { it.intersects(e) } } * 3
                    // Чем дальше от линии размера — тем хуже (длинные выносные через деталь).
                    val cost = (off - p.gap) / p.step + soft + if (side != pref) 1.5 else 0.0
                    if (best == null || cost < best.cost) best = cand.copy(cost = cost)
                    if (soft == 0) break
                }
            }
            val chosen = best ?: buildLinear(d, u, n0 * pref, extent(d.a, u, len, n0 * pref, geometry, circles) + p.gap + 12 * p.step, p)
            texts += chosen.textRect
            dimLines += chosen.lineRect
            extLines += chosen.extRects
            outLinear += chosen.out
        }

        val outDia = ArrayList<DiameterOut>()
        val angles = listOf(-45, -135, 45, 135, -30, -150, 30, 150, -60, -120, 60, 120).map { it * PI / 180 }
        for (d in diameters) {
            var best: Pair<Double, DiameterOut>? = null
            var bestRect: ORect? = null
            for ((idx, ang) in angles.withIndex()) {
                for (extra in 0..2) {
                    val dir = P(cos(ang), sin(ang))
                    val start = d.c + dir * d.r
                    val elbow = d.c + dir * (d.r + p.gap * (1.0 + extra))
                    val w = p.measure(d.text) + p.textH * 0.4
                    val sx = if (dir.x >= 0) 1.0 else -1.0
                    val shelfEnd = elbow + P(sx * w, 0.0)
                    val tc = lerp(elbow, shelfEnd, 0.5) + P(0.0, -p.textH * 0.65)
                    val tr = ORect(tc, P(1.0, 0.0), w / 2, p.textH * 0.55)
                    val leader = ORect.segment(start, elbow, p.textH * 0.05)
                    if (texts.any { it.intersects(tr) } || dimLines.any { it.intersects(tr) } || extLines.any { it.intersects(tr) }) continue
                    val soft = geomRects.count { it.intersects(tr) } * 5 +
                        texts.count { it.intersects(leader) } * 3
                    val cost = idx * 0.3 + extra + soft
                    if (best == null || cost < best.first) {
                        best = cost to DiameterOut(d.id, d.c, d.r, start, elbow, shelfEnd, tc, d.text)
                        bestRect = tr
                    }
                    if (soft == 0) break
                }
                if (best != null && best.first < idx * 0.3 + 0.01) break
            }
            if (best != null) {
                outDia += best.second
                texts += bestRect!!
                dimLines += ORect.segment(best.second.start, best.second.elbow, p.textH * 0.05)
            }
        }
        return Result(outLinear, outDia)
    }

    private data class Candidate(
        val out: LinearOut, val textRect: ORect, val lineRect: ORect, val extRects: List<ORect>, val cost: Double = 0.0,
    )

    private fun buildLinear(d: LinearIn, u: P, n: P, off: Double, p: Params): Candidate {
        val da = d.a + n * off
        val db = d.b + n * off
        val len = dist(d.a, d.b)
        val ru = readable(u)
        // Нормаль «вверх» относительно читаемого текста (ось Y вниз).
        val up = P(ru.y, -ru.x)
        val w = p.measure(d.text)
        val fitsInside = w + p.arrow * 2.5 < len
        val arrowsOutside = len < p.arrow * 2.6
        val base = if (fitsInside) lerp(da, db, 0.5)
        else db + u * (w / 2 + p.arrow * (if (arrowsOutside) 2.2 else 1.0))
        val tc = base + up * (p.textH * 0.65)
        val textRect = ORect(tc, ru, w / 2 + p.textH * 0.2, p.textH * 0.55)
        val lineEndB = if (fitsInside) db else db + u * (w + p.arrow * 2)
        // Концы чуть укорочены, чтобы размеры цепочкой могли стоять на одной линии.
        val trim = p.arrow * 0.3
        val lineRect = ORect.segment(da + u * trim, lineEndB - u * trim, p.textH * 0.1)
        val out = LinearOut(d.id, d.a, d.b, da, db, tc, ru.angle(), d.text, arrowsOutside)
        // Выносные линии (без самого начала у детали — там они касаются контура).
        val ext = listOf(d.a to da, d.b to db).filter { dist(it.first, it.second) > p.textH }
            .map { (s, e) -> ORect.segment(s + (e - s).norm() * (p.textH * 0.5), e, p.textH * 0.05) }
        return Candidate(out, textRect, lineRect, ext)
    }

    /** Насколько далеко геометрия уходит от линии a–b в сторону n в пределах размера. */
    private fun extent(a: P, u: P, len: Double, n: P, geometry: List<Pair<P, P>>, circles: List<Circle>): Double {
        var ext = 0.0
        // Полоса чуть уже размера: линии, лишь касающиеся её края, не мешают.
        val lo = len * 0.01; val hi = len * 0.99
        for ((p, q) in geometry) {
            val tp = (p - a).dot(u); val tq = (q - a).dot(u)
            if ((tp < lo && tq < lo) || (tp > hi && tq > hi)) continue
            val pts = ArrayList<P>(2)
            fun clipAt(t: Double): P = lerp(p, q, (t - tp) / (tq - tp))
            pts += if (tp < lo) clipAt(lo) else if (tp > hi) clipAt(hi) else p
            pts += if (tq < lo) clipAt(lo) else if (tq > hi) clipAt(hi) else q
            for (c in pts) ext = max(ext, (c - a).dot(n))
        }
        for (c in circles) {
            val t = (c.c - a).dot(u)
            if (t >= -c.r && t <= len + c.r) ext = max(ext, (c.c - a).dot(n) + c.r)
        }
        return ext
    }

    private fun parallelOverlap(a: ORect, b: ORect): Boolean =
        abs(a.u.dot(b.u)) > 0.9 && a.intersects(b)
}
