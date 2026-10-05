package ru.konstruktor.eskiz.geom3d

import kotlin.math.abs
import kotlin.math.ceil
import kotlin.math.cos
import kotlin.math.floor
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sin
import kotlin.math.sqrt

/**
 * Простой программный рендер с буфером глубины: заливка граней со светом и тёмные
 * линии острых рёбер. Результат — пиксели ARGB (для Bitmap на телефоне или PNG в тестах).
 */
object Preview {

    fun render(s: Solid, w: Int, h: Int, yaw: Double, pitch: Double, bg: Int = 0xFFECEFF1.toInt()): IntArray {
        val px = IntArray(w * h) { bg }
        if (s.vertices.isEmpty()) return px
        val depth = FloatArray(w * h) { Float.MAX_VALUE }
        val (lo, hi) = s.bounds
        val center = (lo + hi) * 0.5
        val radius = max(1e-6, (hi - lo).len() / 2)
        val k = 0.92 * min(w, h) / (2 * radius)
        val cy = cos(yaw); val sy = sin(yaw); val cp = cos(pitch); val sp = sin(pitch)
        // Поворот: сначала вокруг Z (рыскание), затем вокруг X (наклон). Смотрим вдоль +Y камеры.
        fun cam(v: V3): V3 {
            val d = v - center
            val x1 = d.x * cy - d.y * sy; val y1 = d.x * sy + d.y * cy; val z1 = d.z
            return V3(x1, y1 * cp - z1 * sp, y1 * sp + z1 * cp)
        }
        val cv = s.vertices.map(::cam)
        fun sx(v: V3) = w / 2.0 + v.x * k
        fun sy(v: V3) = h / 2.0 - v.z * k
        val light = V3(-0.35, -0.7, 0.62).unit()

        for ((fi, f) in s.faces.withIndex()) {
            val n = cam(f.normal + center) // поворачиваем направление (center сокращается)
            if (n.y > 1e-9) continue // грань смотрит от нас
            val inten = 0.30 + 0.70 * max(0.0, n.dot(light))
            val col = shade(0xFF4A86C8.toInt(), inten)
            // Треугольники этой грани.
            for (t in s.faceTriangles[fi]) {
                tri(px, depth, w, h, cv[t[0]], cv[t[1]], cv[t[2]], col, ::sx, ::sy)
            }
        }

        // Острые рёбра (между гранями с углом > 20°) — линиями.
        val faceOf = HashMap<Long, MutableList<V3>>()
        for (f in s.faces) for (l in listOf(f.outer) + f.holes) for (i in l.indices) {
            val a = l[i]; val b = l[(i + 1) % l.size]
            faceOf.getOrPut(minOf(a, b).toLong() shl 32 or maxOf(a, b).toLong()) { mutableListOf() } += f.normal
        }
        val bias = (radius * 0.004).toFloat()
        for ((key, normals) in faceOf) {
            val sharp = normals.size < 2 || normals[0].dot(normals[1]) < cos(Math.toRadians(20.0))
            if (!sharp) continue
            val a = cv[(key shr 32).toInt()]; val b = cv[key.toInt()]
            line(px, depth, w, h, a, b, 0xFF1A2733.toInt(), bias, ::sx, ::sy)
        }
        return px
    }

    private fun shade(c: Int, k: Double): Int {
        val r = ((c shr 16 and 0xFF) * k).toInt().coerceIn(0, 255)
        val g = ((c shr 8 and 0xFF) * k).toInt().coerceIn(0, 255)
        val b = ((c and 0xFF) * k).toInt().coerceIn(0, 255)
        return (0xFF shl 24) or (r shl 16) or (g shl 8) or b
    }

    private inline fun tri(
        px: IntArray, depth: FloatArray, w: Int, h: Int, a: V3, b: V3, c: V3, col: Int,
        sx: (V3) -> Double, sy: (V3) -> Double,
    ) {
        val x0 = sx(a); val y0 = sy(a); val x1 = sx(b); val y1 = sy(b); val x2 = sx(c); val y2 = sy(c)
        val area = (x1 - x0) * (y2 - y0) - (y1 - y0) * (x2 - x0)
        if (abs(area) < 1e-12) return
        val minX = max(0, floor(min(x0, min(x1, x2))).toInt()); val maxX = min(w - 1, ceil(max(x0, max(x1, x2))).toInt())
        val minY = max(0, floor(min(y0, min(y1, y2))).toInt()); val maxY = min(h - 1, ceil(max(y0, max(y1, y2))).toInt())
        for (y in minY..maxY) {
            val py = y + 0.5
            for (x in minX..maxX) {
                val pxx = x + 0.5
                val w0 = ((x1 - pxx) * (y2 - py) - (y1 - py) * (x2 - pxx)) / area
                val w1 = ((x2 - pxx) * (y0 - py) - (y2 - py) * (x0 - pxx)) / area
                val w2 = 1 - w0 - w1
                if (w0 < -1e-9 || w1 < -1e-9 || w2 < -1e-9) continue
                val d = (w0 * a.y + w1 * b.y + w2 * c.y).toFloat()
                val i = y * w + x
                if (d < depth[i]) { depth[i] = d; px[i] = col }
            }
        }
    }

    private inline fun line(
        px: IntArray, depth: FloatArray, w: Int, h: Int, a: V3, b: V3, col: Int, bias: Float,
        sx: (V3) -> Double, sy: (V3) -> Double,
    ) {
        val x0 = sx(a); val y0 = sy(a); val x1 = sx(b); val y1 = sy(b)
        val steps = max(1, ceil(sqrt((x1 - x0) * (x1 - x0) + (y1 - y0) * (y1 - y0))).toInt() * 2)
        for (sI in 0..steps) {
            val t = sI.toDouble() / steps
            val x = (x0 + (x1 - x0) * t).toInt(); val y = (y0 + (y1 - y0) * t).toInt()
            if (x < 0 || y < 0 || x >= w || y >= h) continue
            val d = (a.y + (b.y - a.y) * t).toFloat()
            val i = y * w + x
            if (d - bias <= depth[i]) { px[i] = col; depth[i] = minOf(depth[i], d - bias) }
        }
    }
}
