package ru.konstruktor.eskiz.geom

import kotlin.math.abs
import kotlin.math.exp
import kotlin.math.ln
import kotlin.math.max
import kotlin.math.sqrt

/**
 * Известный размер на фото — ограничение для калибровки.
 * [predict] получает функцию «пиксель → мм» и возвращает размер по текущей модели.
 */
sealed class Constraint(val id: Int, val known: Double) {
    abstract fun predict(f: (P) -> P): Double
}

class LinearConstraint(id: Int, val a: P, val b: P, known: Double) : Constraint(id, known) {
    override fun predict(f: (P) -> P) = dist(f(a), f(b))
}

class DiameterConstraint(id: Int, val pts: List<P>, known: Double) : Constraint(id, known) {
    override fun predict(f: (P) -> P) = (fitCircle(pts.map(f))?.r ?: 0.0) * 2
}

enum class CalibMode {
    /** Нет ни одного известного размера: всё в пикселях. */
    NONE,
    /** Известен в основном масштаб: погрешность больше 4% или неизвестна. */
    SCALE,
    /** Приблизительная калибровка: погрешность 1–4%. */
    TILT,
    /** Точная калибровка: погрешность до 1%. */
    FULL,
}

/**
 * Модель «пиксели фото → мм на плоскости детали»:
 *   мм = S · A · Pr · B · пиксель, x = [ln s, a, b, l1, l2], где
 *   B  — нормировка (или гомография листа-мишени),
 *   Pr — проективная часть (наклон камеры, l1, l2),
 *   A  — аффинная часть с точностью до подобия (a, b),
 *   S  — масштаб.
 */
internal class Model(val base: Mat3) {
    fun matrix(x: DoubleArray): Mat3 {
        val sm = Mat3.scale(exp(x[0]))
        val am = Mat3(doubleArrayOf(1 + x[1], x[2], 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0))
        val pm = Mat3(doubleArrayOf(1.0, 0.0, 0.0, 0.0, 1.0, 0.0, x[3], x[4], 1.0))
        return sm * am * pm * base
    }
}

/** Оценка параметров и их ковариация (5×5). */
internal class Fit(val model: Model, val x: DoubleArray, val cov: Array<DoubleArray>) {
    val h = model.matrix(x)

    fun predict(c: (f: (P) -> P) -> Double): Double = c { h.apply(it) }

    /** Стандартное отклонение величины, вычисляемой по модели. */
    fun sigma(c: (f: (P) -> P) -> Double): Double {
        val g = DoubleArray(5)
        for (j in 0..4) {
            if (cov[j][j] == 0.0) continue
            val d = 1e-6
            val mp = model.matrix(x.copyOf().also { it[j] += d })
            val mm = model.matrix(x.copyOf().also { it[j] -= d })
            g[j] = (c { mp.apply(it) } - c { mm.apply(it) }) / (2 * d)
        }
        var s = 0.0
        for (i in 0..4) for (j in 0..4) s += g[i] * cov[i][j] * g[j]
        return sqrt(max(0.0, s))
    }
}

/**
 * Результат калибровки. Погрешность каждого вычисленного размера считается честно —
 * по ковариации параметров: если введённых размеров не хватает (например, только стороны
 * контура без диагоналей), погрешность будет большой.
 */
class Calibration internal constructor(
    private val fit: Fit?,
    val mode: CalibMode,
    val sheet: Boolean,
    /** Сколько введённых размеров использовано. */
    val usedCount: Int,
    /** Типичная относительная погрешность по полю снимка (0.003 = 0.3%), null — оценить нельзя. */
    val sigmaRel: Double?,
    /** Размеры, которые не согласуются с остальными: id → значение по остальным размерам. */
    val outliers: Map<Int, Double>,
) {
    val h: Mat3 = fit?.h ?: Mat3.I
    val calibrated get() = fit != null

    fun toMm(p: P) = h.apply(p)

    /** Сколько мм приходится на пиксель в окрестности точки. */
    fun mmPerPx(p: P): Double {
        val a = toMm(p)
        return (dist(a, toMm(p + P(1.0, 0.0))) + dist(a, toMm(p + P(0.0, 1.0)))) / 2
    }

    /** Погрешность вычисленного размера между двумя точками фото, мм. */
    fun uncertainty(a: P, b: P): Double? {
        val f = fit ?: return null
        val model = f.sigma { m -> dist(m(a), m(b)) }
        val pick = PICK_PX * mmPerPx(lerp(a, b, 0.5))
        return sqrt(model * model + 2 * pick * pick)
    }

    /** Погрешность вычисленного диаметра, мм. */
    fun circleUncertainty(pts: List<P>): Double? {
        val f = fit ?: return null
        val model = f.sigma { m -> (fitCircle(pts.map(m))?.r ?: 0.0) * 2 }
        val c = fitCircle(pts) ?: return model
        val pick = PICK_PX * mmPerPx(c.c)
        return sqrt(model * model + pick * pick)
    }

    companion object {
        /** Погрешность установки точки пальцем с лупой и привязкой, пикс. */
        const val PICK_PX = 1.5
        val NONE = Calibration(null, CalibMode.NONE, false, 0, null, emptyMap())
    }
}

object Calibrator {
    /** Ожидаемая погрешность введённого размера (замер + положение точек), относительная. */
    private const val SIG_MEAS = 0.003

    // Априорные разбросы параметров [ln s, a, b, l1, l2] в нормированных координатах.
    private val PRIOR_FREE = doubleArrayOf(0.0, 0.2, 0.2, 0.6, 0.6)
    private val PRIOR_SHEET = doubleArrayOf(0.003, 0.01, 0.01, 0.02, 0.02)

    /** Нормировка для режима с листом, мм. */
    private const val SHEET_NORM = 300.0

    fun calibrate(imageW: Int, imageH: Int, sheetH: Mat3?, constraints: List<Constraint>): Calibration {
        val sheet = sheetH != null
        val model = Model(baseTransform(imageW, imageH, sheetH))
        val all = constraints.filter { it.known > 0 }
        val n = all.size
        if (n == 0 && !sheet) return Calibration.NONE

        // Поиск ошибочных размеров: убираем по одному тот, который хуже всего согласуется
        // с остальными (с учётом того, насколько остальные вообще определяют его значение).
        val outliers = HashMap<Int, Double>()
        var active = all
        while (active.size >= 3 && outliers.size < n / 3 + 1) {
            var bestC: Constraint? = null
            var bestPred = 0.0
            var bestZ = 0.0
            for (c in active) {
                val f = fit(active.filter { it !== c }, model, sheet)
                val pred = f.predict(c::predict)
                val sp = f.sigma(c::predict)
                val err = abs(pred - c.known)
                val z = err / sqrt(sp * sp + (SIG_MEAS * c.known).let { it * it })
                if (z > 4 && err / c.known > 0.015 && err > 0.5 && z > bestZ) {
                    bestZ = z; bestC = c; bestPred = pred
                }
            }
            if (bestC == null) break
            outliers[bestC.id] = bestPred
            active = active.filter { it !== bestC }
        }
        if (n == 2) {
            val pred = fit(listOf(all[0]), model, sheet).predict(all[1]::predict)
            val err = abs(pred - all[1].known)
            if (err / all[1].known > 0.02 && err > 0.5) {
                outliers[all[0].id] = fit(listOf(all[1]), model, sheet).predict(all[0]::predict)
                outliers[all[1].id] = pred
            }
        }

        // При малом числе размеров ошибочный только подсвечивается, но не исключается.
        val used = if (n >= 5) active else all
        val f = fit(used, model, sheet)

        // Типичная погрешность: отрезки через всё поле снимка.
        val w = imageW.toDouble(); val hh = imageH.toDouble()
        val probes = listOf(
            P(w * 0.1, hh * 0.5) to P(w * 0.9, hh * 0.5),
            P(w * 0.5, hh * 0.1) to P(w * 0.5, hh * 0.9),
            P(w * 0.15, hh * 0.15) to P(w * 0.85, hh * 0.85),
            P(w * 0.85, hh * 0.15) to P(w * 0.15, hh * 0.85),
        )
        val rel = probes.maxOf { (a, b) ->
            val v = f.predict { m -> dist(m(a), m(b)) }
            f.sigma { m -> dist(m(a), m(b)) } / max(1e-9, v)
        }
        val sigmaRel = if (n == 1 && !sheet) null else max(0.001, rel)

        val mode = when {
            sigmaRel == null -> CalibMode.SCALE
            sigmaRel <= 0.01 -> CalibMode.FULL
            sigmaRel <= 0.04 -> CalibMode.TILT
            else -> CalibMode.SCALE
        }
        return Calibration(f, mode, sheet, used.size, sigmaRel, outliers)
    }

    private fun baseTransform(w: Int, h: Int, sheetH: Mat3?): Mat3 =
        if (sheetH != null) {
            Mat3.scale(1 / SHEET_NORM) * Mat3.translate(-105.0, -148.5) * sheetH
        } else {
            val f = max(w, h).toDouble()
            Mat3.scale(1 / f) * Mat3.translate(-w / 2.0, -h / 2.0)
        }

    /** Оценка параметров с априорными ограничениями и их ковариация. */
    private fun fit(cs: List<Constraint>, model: Model, sheet: Boolean): Fit {
        val prior = if (sheet) PRIOR_SHEET else PRIOR_FREE
        val priorMean = DoubleArray(5).also { if (sheet) it[0] = ln(SHEET_NORM) }
        val x = priorMean.copyOf()
        if (cs.isNotEmpty() && !sheet) {
            // Начальный масштаб — медиана отношений.
            val m0 = model.matrix(x)
            val ratios = cs.map { c -> c.known / max(1e-9, c.predict { m0.apply(it) }) }.sorted()
            x[0] = ln(ratios[ratios.size / 2])
        }
        val res = { v: DoubleArray ->
            val m = model.matrix(v)
            val r = DoubleArray(cs.size + 5)
            cs.forEachIndexed { i, c -> r[i] = (c.predict { m.apply(it) } - c.known) / c.known / SIG_MEAS }
            for (p in 0..4) r[cs.size + p] = if (prior[p] > 0) (v[p] - priorMean[p]) / prior[p] else 0.0
            r
        }
        val xf = levenbergMarquardt(x, res)

        // Ковариация: (JᵀJ)⁻¹, масштабированная по фактическому разбросу.
        val j = jacobian(xf, res)
        val a = Array(5) { u -> DoubleArray(5) { v -> var s = 0.0; for (row in j) s += row[u] * row[v]; s } }
        val cov = invert(a) ?: Array(5) { u -> DoubleArray(5) { v -> if (u == v) 1.0 else 0.0 } }
        val r = res(xf)
        val chi2 = (cs.indices).sumOf { r[it] * r[it] }
        val dof = cs.size - (if (sheet) 0 else 1)
        val scale = if (dof > 0) max(1.0, chi2 / dof) else 1.0
        for (u in 0..4) for (v in 0..4) cov[u][v] *= scale
        return Fit(model, xf, cov)
    }

    private fun jacobian(x: DoubleArray, res: (DoubleArray) -> DoubleArray): Array<DoubleArray> {
        val r0 = res(x)
        val j = Array(r0.size) { DoubleArray(5) }
        for (p in 0..4) {
            val h = 1e-6 * max(1.0, abs(x[p]))
            val rp = res(x.copyOf().also { it[p] += h })
            val rm = res(x.copyOf().also { it[p] -= h })
            for (i in r0.indices) j[i][p] = (rp[i] - rm[i]) / (2 * h)
        }
        return j
    }

    private fun invert(a: Array<DoubleArray>): Array<DoubleArray>? {
        val n = a.size
        val cols = (0 until n).map { c -> solveLinear(a, DoubleArray(n) { if (it == c) 1.0 else 0.0 }) ?: return null }
        return Array(n) { i -> DoubleArray(n) { j -> cols[j][i] } }
    }

    private fun levenbergMarquardt(x0: DoubleArray, res: (DoubleArray) -> DoubleArray): DoubleArray {
        var x = x0.copyOf()
        var r = res(x)
        var cost = r.sumOf { it * it }
        var lambda = 1e-3
        repeat(100) {
            val j = jacobian(x, res)
            val a = Array(5) { DoubleArray(5) }
            val g = DoubleArray(5)
            for (i in r.indices) for (u in 0..4) {
                g[u] += j[i][u] * r[i]
                for (v in 0..4) a[u][v] += j[i][u] * j[i][v]
            }
            var improved = false
            while (lambda < 1e10) {
                val aa = Array(5) { u -> DoubleArray(5) { v -> a[u][v] + if (u == v) lambda * a[u][u] + 1e-12 else 0.0 } }
                val d = solveLinear(aa, DoubleArray(5) { -g[it] })
                if (d == null) { lambda *= 4; continue }
                val xn = DoubleArray(5) { x[it] + d[it] }
                val rn = res(xn)
                val cn = rn.sumOf { it * it }
                if (cn.isFinite() && cn < cost) {
                    val gain = cost - cn
                    x = xn; r = rn; cost = cn
                    lambda = max(1e-9, lambda / 3)
                    improved = gain > 1e-12 * max(1.0, cost)
                    break
                }
                lambda *= 4
            }
            if (!improved) return x
        }
        return x
    }
}
