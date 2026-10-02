package ru.konstruktor.eskiz.geom

import kotlinx.serialization.Serializable
import kotlin.math.abs
import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.hypot
import kotlin.math.sin
import kotlin.math.sqrt

@Serializable
data class P(val x: Double, val y: Double) {
    operator fun plus(o: P) = P(x + o.x, y + o.y)
    operator fun minus(o: P) = P(x - o.x, y - o.y)
    operator fun times(k: Double) = P(x * k, y * k)
    operator fun div(k: Double) = P(x / k, y / k)
    operator fun unaryMinus() = P(-x, -y)
    fun dot(o: P) = x * o.x + y * o.y
    fun cross(o: P) = x * o.y - y * o.x
    fun len() = hypot(x, y)
    fun norm(): P { val l = len(); return if (l < 1e-12) P(1.0, 0.0) else P(x / l, y / l) }
    /** Поворот на +90° в системе с осью Y вниз (как на экране). */
    fun perp() = P(-y, x)
    fun angle() = atan2(y, x)
    fun rotate(a: Double): P { val c = cos(a); val s = sin(a); return P(x * c - y * s, x * s + y * c) }
}

fun dist(a: P, b: P) = hypot(a.x - b.x, a.y - b.y)

fun lerp(a: P, b: P, t: Double) = P(a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t)

/** Расстояние от точки до отрезка. */
fun distToSegment(p: P, a: P, b: P): Double {
    val d = b - a
    val l2 = d.dot(d)
    if (l2 < 1e-12) return dist(p, a)
    val t = ((p - a).dot(d) / l2).coerceIn(0.0, 1.0)
    return dist(p, a + d * t)
}

/** Матрица 3×3 построчно — проективное преобразование плоскости. */
class Mat3(val m: DoubleArray) {
    init { require(m.size == 9) }

    operator fun times(o: Mat3): Mat3 {
        val r = DoubleArray(9)
        for (i in 0..2) for (j in 0..2) {
            var s = 0.0
            for (k in 0..2) s += m[i * 3 + k] * o.m[k * 3 + j]
            r[i * 3 + j] = s
        }
        return Mat3(r)
    }

    fun apply(p: P): P {
        val w = m[6] * p.x + m[7] * p.y + m[8]
        return P((m[0] * p.x + m[1] * p.y + m[2]) / w, (m[3] * p.x + m[4] * p.y + m[5]) / w)
    }

    fun inverse(): Mat3 {
        val a = m
        val c00 = a[4] * a[8] - a[5] * a[7]
        val c01 = a[5] * a[6] - a[3] * a[8]
        val c02 = a[3] * a[7] - a[4] * a[6]
        val det = a[0] * c00 + a[1] * c01 + a[2] * c02
        val inv = doubleArrayOf(
            c00, a[2] * a[7] - a[1] * a[8], a[1] * a[5] - a[2] * a[4],
            c01, a[0] * a[8] - a[2] * a[6], a[2] * a[3] - a[0] * a[5],
            c02, a[1] * a[6] - a[0] * a[7], a[0] * a[4] - a[1] * a[3],
        )
        return Mat3(DoubleArray(9) { inv[it] / det })
    }

    companion object {
        val I = Mat3(doubleArrayOf(1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0))
        fun translate(x: Double, y: Double) = Mat3(doubleArrayOf(1.0, 0.0, x, 0.0, 1.0, y, 0.0, 0.0, 1.0))
        fun scale(s: Double) = Mat3(doubleArrayOf(s, 0.0, 0.0, 0.0, s, 0.0, 0.0, 0.0, 1.0))
        fun rotate(a: Double): Mat3 {
            val c = cos(a); val s = sin(a)
            return Mat3(doubleArrayOf(c, -s, 0.0, s, c, 0.0, 0.0, 0.0, 1.0))
        }
    }
}

data class Circle(val c: P, val r: Double)

/** Окружность по точкам (алгебраический метод Каса). Нужно минимум 3 точки. */
fun fitCircle(pts: List<P>): Circle? {
    if (pts.size < 3) return null
    // Центрируем для устойчивости.
    val cx = pts.sumOf { it.x } / pts.size
    val cy = pts.sumOf { it.y } / pts.size
    var suu = 0.0; var svv = 0.0; var suv = 0.0
    var suuu = 0.0; var svvv = 0.0; var suvv = 0.0; var svuu = 0.0
    for (p in pts) {
        val u = p.x - cx; val v = p.y - cy
        suu += u * u; svv += v * v; suv += u * v
        suuu += u * u * u; svvv += v * v * v; suvv += u * v * v; svuu += v * u * u
    }
    val det = suu * svv - suv * suv
    if (abs(det) < 1e-12) return null
    val b1 = 0.5 * (suuu + suvv)
    val b2 = 0.5 * (svvv + svuu)
    val uc = (b1 * svv - b2 * suv) / det
    val vc = (suu * b2 - suv * b1) / det
    val r = sqrt(uc * uc + vc * vc + (suu + svv) / pts.size)
    return Circle(P(uc + cx, vc + cy), r)
}

/** Решение системы A·x = b методом Гаусса с выбором главного элемента. */
fun solveLinear(a: Array<DoubleArray>, b: DoubleArray): DoubleArray? {
    val n = b.size
    val m = Array(n) { i -> DoubleArray(n + 1) { j -> if (j < n) a[i][j] else b[i] } }
    for (col in 0 until n) {
        var piv = col
        for (r in col + 1 until n) if (abs(m[r][col]) > abs(m[piv][col])) piv = r
        if (abs(m[piv][col]) < 1e-15) return null
        val t = m[piv]; m[piv] = m[col]; m[col] = t
        for (r in 0 until n) if (r != col) {
            val f = m[r][col] / m[col][col]
            if (f != 0.0) for (c in col..n) m[r][c] -= f * m[col][c]
        }
    }
    return DoubleArray(n) { m[it][n] / m[it][it] }
}
