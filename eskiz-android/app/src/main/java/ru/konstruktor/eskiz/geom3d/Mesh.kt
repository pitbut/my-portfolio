package ru.konstruktor.eskiz.geom3d

import ru.konstruktor.eskiz.geom.P
import kotlin.math.abs
import kotlin.math.max

/** Разбиение простого многоугольника (обход против часовой) на треугольники «отрезанием ушей». */
object Triangulate {
    fun simple(pts: List<P>): List<IntArray> {
        val idx = ArrayList((pts.indices).toList())
        val out = ArrayList<IntArray>()
        fun cross(o: P, a: P, b: P) = (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x)
        fun inside(p: P, a: P, b: P, c: P): Boolean =
            cross(a, b, p) >= -1e-12 && cross(b, c, p) >= -1e-12 && cross(c, a, p) >= -1e-12
        var guard = 0
        while (idx.size > 3 && guard++ < 100000) {
            var cut = false
            for (i in idx.indices) {
                val ia = idx[(i + idx.size - 1) % idx.size]; val ib = idx[i]; val ic = idx[(i + 1) % idx.size]
                val a = pts[ia]; val b = pts[ib]; val c = pts[ic]
                val cr = cross(a, b, c)
                if (cr <= 1e-12) continue // вогнутая или вырожденная вершина
                // Совпадающие точки (концы «мостиков» к отверстиям) ухо не блокируют.
                fun same(p: P, q: P) = abs(p.x - q.x) < 1e-9 && abs(p.y - q.y) < 1e-9
                val blocked = idx.any { k ->
                    k != ia && k != ib && k != ic && !same(pts[k], a) && !same(pts[k], b) && !same(pts[k], c) && inside(pts[k], a, b, c)
                }
                if (blocked) continue
                out += intArrayOf(ia, ib, ic)
                idx.removeAt(i)
                cut = true
                break
            }
            if (!cut) {
                // Остались вырожденные вершины — отрезаем любую, чтобы не зациклиться.
                val i = idx.indices.minByOrNull { j ->
                    abs(cross(pts[idx[(j + idx.size - 1) % idx.size]], pts[idx[j]], pts[idx[(j + 1) % idx.size]]))
                }!!
                idx.removeAt(i)
            }
        }
        if (idx.size == 3 && cross(pts[idx[0]], pts[idx[1]], pts[idx[2]]) > 1e-12) out += intArrayOf(idx[0], idx[1], idx[2])
        return out
    }

    fun area(pts: List<P>): Double {
        var s = 0.0
        for (i in pts.indices) { val a = pts[i]; val b = pts[(i + 1) % pts.size]; s += a.x * b.y - b.x * a.y }
        return s / 2
    }

    /** Убирает повторы и точки на одной прямой с соседями. */
    fun clean(pts: List<P>, eps: Double = 1e-6): List<P> {
        var cur = pts
        var changed = true
        while (changed && cur.size > 3) {
            changed = false
            val out = ArrayList<P>()
            for (i in cur.indices) {
                val a = cur[(i + cur.size - 1) % cur.size]; val b = cur[i]; val c = cur[(i + 1) % cur.size]
                val ab = b - a; val bc = c - b
                val degenerate = ab.len() < eps || abs(ab.cross(bc)) < eps * max(1.0, ab.len() + bc.len()) && ab.dot(bc) > 0
                if (degenerate) changed = true else out += b
            }
            cur = out
        }
        return cur
    }
}

/**
 * Призма: замкнутый контур в плоскости (a, b), вытянутый вдоль t от [t0] до [t1],
 * отображённый в мировые оси [ea], [eb], [et]. Нормали граней наружу.
 */
fun prism(loop: List<P>, t0: Double, t1: Double, ea: V3, eb: V3, et: V3): List<Csg.Poly> {
    var pts = Triangulate.clean(loop)
    if (Triangulate.area(pts) < 0) pts = pts.reversed()
    fun w(p: P, t: Double) = ea * p.x + eb * p.y + et * t
    val polys = ArrayList<List<V3>>()
    for (tri in Triangulate.simple(pts)) {
        polys += listOf(w(pts[tri[0]], t1), w(pts[tri[1]], t1), w(pts[tri[2]], t1))
        polys += listOf(w(pts[tri[2]], t0), w(pts[tri[1]], t0), w(pts[tri[0]], t0))
    }
    for (i in pts.indices) {
        val p = pts[i]; val q = pts[(i + 1) % pts.size]
        polys += listOf(w(p, t0), w(q, t0), w(q, t1), w(p, t1))
    }
    // Левая тройка осей переворачивает нормали — возвращаем их наружу.
    val det = ea.dot(eb.cross(et))
    return polys.map { Csg.Poly(if (det < 0) it.reversed() else it) }
}

/**
 * Чистая многогранная модель: общие вершины, грани — плоские многоугольники (возможно с отверстиями),
 * каждое ребро принадлежит ровно двум граням.
 */
class Solid(val vertices: List<V3>, val faces: List<Face>) {
    /** Грань: внешний контур (против часовой вокруг нормали) и отверстия; индексы вершин. */
    class Face(val normal: V3, val outer: IntArray, val holes: List<IntArray>)

    /** Треугольники каждой грани (для просмотра и STL). */
    val faceTriangles: List<List<IntArray>> by lazy {
        faces.map { f ->
            val (u, v) = basis(f.normal)
            fun p2(i: Int) = vertices[i].let { P(it.dot(u), it.dot(v)) }
            val loop = mergeHoles(f.outer.toList(), f.holes.map { it.toList() }, ::p2)
            Triangulate.simple(loop.map(::p2)).map { t -> intArrayOf(loop[t[0]], loop[t[1]], loop[t[2]]) }
        }
    }

    val triangles: List<IntArray> by lazy { faceTriangles.flatten() }

    val volume: Double by lazy {
        triangles.sumOf { t -> vertices[t[0]].dot(vertices[t[1]].cross(vertices[t[2]])) } / 6
    }

    val bounds: Pair<V3, V3> by lazy {
        V3(vertices.minOf { it.x }, vertices.minOf { it.y }, vertices.minOf { it.z }) to
            V3(vertices.maxOf { it.x }, vertices.maxOf { it.y }, vertices.maxOf { it.z })
    }

    companion object {
        fun basis(n: V3): Pair<V3, V3> {
            val ref = if (abs(n.x) < 0.9) V3(1.0, 0.0, 0.0) else V3(0.0, 1.0, 0.0)
            val u = ref.cross(n).unit()
            val v = n.cross(u)
            return u to v
        }

        /** Соединяет отверстия с внешним контуром «мостиками», чтобы получить один простой контур. */
        fun mergeHoles(outer: List<Int>, holes: List<List<Int>>, p2: (Int) -> P): List<Int> {
            var poly = outer
            for (h in holes.sortedByDescending { hole -> hole.maxOf { p2(it).x } }) {
                val hi = h.indices.maxByOrNull { p2(h[it]).x }!!
                val m = p2(h[hi])
                // Ближайшая видимая вершина внешнего контура (без пересечений с рёбрами).
                val cand = poly.indices.sortedBy { (p2(poly[it]) - m).len() }.firstOrNull { k ->
                    val a = p2(poly[k])
                    val segs = poly.indices.map { poly[it] to poly[(it + 1) % poly.size] } + h.indices.map { h[it] to h[(it + 1) % h.size] }
                    segs.none { (s, e) -> s != poly[k] && e != poly[k] && s != h[hi] && e != h[hi] && crosses(m, a, p2(s), p2(e)) }
                } ?: 0
                val ring = (0..h.size).map { h[(hi + it) % h.size] }
                poly = poly.subList(0, cand + 1) + ring + poly.subList(cand, poly.size)
            }
            return poly
        }

        private fun crosses(a: P, b: P, c: P, d: P): Boolean {
            fun cr(o: P, p: P, q: P) = (p.x - o.x) * (q.y - o.y) - (p.y - o.y) * (q.x - o.x)
            val d1 = cr(c, d, a); val d2 = cr(c, d, b); val d3 = cr(a, b, c); val d4 = cr(a, b, d)
            return ((d1 > 1e-12 && d2 < -1e-12) || (d1 < -1e-12 && d2 > 1e-12)) &&
                ((d3 > 1e-12 && d4 < -1e-12) || (d3 < -1e-12 && d4 > 1e-12))
        }

        /**
         * Из «супа» выпуклых многоугольников после CSG: сварка вершин, устранение Т-стыков,
         * объединение соседних граней в одной плоскости, удаление лишних вершин на прямых.
         */
        fun fromPolygons(polys: List<Csg.Poly>, tol: Double = 2e-5): Solid {
            // 1. Сварка вершин.
            val verts = ArrayList<V3>()
            val grid = HashMap<Triple<Long, Long, Long>, MutableList<Int>>()
            val cell = tol * 4
            fun key(v: V3, dx: Int = 0, dy: Int = 0, dz: Int = 0) =
                Triple(Math.floor(v.x / cell).toLong() + dx, Math.floor(v.y / cell).toLong() + dy, Math.floor(v.z / cell).toLong() + dz)
            fun vid(v: V3): Int {
                for (dx in -1..1) for (dy in -1..1) for (dz in -1..1) {
                    grid[key(v, dx, dy, dz)]?.forEach { i -> if ((verts[i] - v).len() <= tol) return i }
                }
                verts += v
                grid.getOrPut(key(v)) { mutableListOf() } += verts.size - 1
                return verts.size - 1
            }
            class F(var loop: MutableList<Int>, val plane: Csg.Plane)
            var faces = polys.mapNotNull { p ->
                val ids = ArrayList<Int>()
                for (v in p.v) { val i = vid(v); if (ids.isEmpty() || ids.last() != i) ids += i }
                while (ids.size > 1 && ids.first() == ids.last()) ids.removeAt(ids.size - 1)
                if (ids.size >= 3) F(ids, p.plane) else null
            }

            // 2. Т-стыки: вставляем в рёбра вершины, лежащие на них.
            val sortedByX = verts.indices.sortedBy { verts[it].x }
            val xs = DoubleArray(sortedByX.size) { verts[sortedByX[it]].x }
            fun onSegment(a: Int, b: Int): List<Int> {
                val pa = verts[a]; val pb = verts[b]
                val d = pb - pa; val l2 = d.dot(d)
                if (l2 < tol * tol) return emptyList()
                val lo = minOf(pa.x, pb.x) - tol; val hi = maxOf(pa.x, pb.x) + tol
                var s = java.util.Arrays.binarySearch(xs, lo).let { if (it < 0) -it - 1 else it }
                val res = ArrayList<Pair<Double, Int>>()
                while (s < xs.size && xs[s] <= hi) {
                    val i = sortedByX[s++]
                    if (i == a || i == b) continue
                    val t = (verts[i] - pa).dot(d) / l2
                    if (t <= 1e-9 || t >= 1 - 1e-9) continue
                    if ((pa + d * t - verts[i]).len() <= tol) res += t to i
                }
                return res.sortedBy { it.first }.map { it.second }
            }
            for (f in faces) {
                val out = ArrayList<Int>()
                for (k in f.loop.indices) {
                    val a = f.loop[k]; val b = f.loop[(k + 1) % f.loop.size]
                    out += a; out += onSegment(a, b)
                }
                f.loop = out
            }

            // 3. Объединение граней в одной плоскости (по общим рёбрам).
            val groups = ArrayList<MutableList<F>>()
            for (f in faces) {
                val g = groups.firstOrNull { g ->
                    val p = g[0].plane
                    p.n.dot(f.plane.n) > 1 - 1e-9 && abs(p.w - f.plane.w) < tol * 5
                }
                if (g != null) g += f else groups += mutableListOf(f)
            }
            val result = ArrayList<Pair<V3, List<IntArray>>>()
            for (g in groups) {
                // Рёбра внутри группы, встречающиеся в обе стороны, — внутренние, их убираем.
                val directed = HashMap<Long, Int>()
                fun code(a: Int, b: Int) = a.toLong() shl 32 or b.toLong()
                for (f in g) for (k in f.loop.indices) {
                    val c = code(f.loop[k], f.loop[(k + 1) % f.loop.size])
                    directed[c] = (directed[c] ?: 0) + 1
                }
                val boundary = HashMap<Int, MutableList<Int>>()
                for (f in g) for (k in f.loop.indices) {
                    val a = f.loop[k]; val b = f.loop[(k + 1) % f.loop.size]
                    if (directed.containsKey(code(b, a))) continue
                    boundary.getOrPut(a) { mutableListOf() } += b
                }
                val loops = ArrayList<IntArray>()
                while (boundary.isNotEmpty()) {
                    val start = boundary.keys.first()
                    val loop = ArrayList<Int>()
                    var cur = start
                    var guard = 0
                    while (guard++ < 100000) {
                        loop += cur
                        val nexts = boundary[cur] ?: break
                        val nx = nexts.removeAt(0)
                        if (nexts.isEmpty()) boundary.remove(cur)
                        cur = nx
                        if (cur == start) break
                    }
                    if (loop.size >= 3) loops += loop.toIntArray()
                }
                result += g[0].plane.n to loops
            }

            // 4. Лишние вершины на прямых (степень 2 во всём теле).
            val degree = HashMap<Int, MutableSet<Int>>()
            for ((_, loops) in result) for (l in loops) for (k in l.indices) {
                val a = l[k]; val b = l[(k + 1) % l.size]
                degree.getOrPut(a) { HashSet() } += b; degree.getOrPut(b) { HashSet() } += a
            }
            fun removable(prev: Int, v: Int, next: Int): Boolean {
                if ((degree[v]?.size ?: 0) != 2) return false
                val d1 = verts[v] - verts[prev]; val d2 = verts[next] - verts[v]
                return d1.cross(d2).len() <= 1e-9 * max(1.0, d1.len() * d2.len()) && d1.dot(d2) > 0
            }
            val cleaned = result.map { (n, loops) ->
                n to loops.map { l ->
                    val keep = l.indices.filter { k -> !removable(l[(k + l.size - 1) % l.size], l[k], l[(k + 1) % l.size]) }
                    IntArray(keep.size) { l[keep[it]] }
                }.filter { it.size >= 3 }
            }

            // 5. Внешний контур и отверстия каждой грани (в плоском базисе грани).
            val outFaces = ArrayList<Face>()
            for ((n, loops) in cleaned) {
                val (u, v) = basis(n)
                fun area(l: IntArray) = Triangulate.area(l.map { P(verts[it].dot(u), verts[it].dot(v)) })
                val outers = loops.filter { area(it) > 0 }
                val holes = loops.filter { area(it) <= 0 }
                for (o in outers) {
                    val op = o.map { P(verts[it].dot(u), verts[it].dot(v)) }
                    val mine = if (outers.size == 1) holes else holes.filter { h ->
                        val hp = P(verts[h[0]].dot(u), verts[h[0]].dot(v))
                        pointInPoly(hp, op)
                    }
                    outFaces += Face(n, o, mine)
                }
            }
            // Оставляем только используемые вершины.
            val used = outFaces.flatMap { f -> f.outer.toList() + f.holes.flatMap { it.toList() } }.distinct().sorted()
            val remap = HashMap<Int, Int>().apply { used.forEachIndexed { i, v -> put(v, i) } }
            return Solid(used.map { verts[it] }, outFaces.map { f ->
                Face(f.normal, IntArray(f.outer.size) { remap[f.outer[it]]!! }, f.holes.map { h -> IntArray(h.size) { remap[h[it]]!! } })
            })
        }

        fun pointInPoly(p: P, poly: List<P>): Boolean {
            var c = false
            var j = poly.size - 1
            for (i in poly.indices) {
                val a = poly[i]; val b = poly[j]
                if ((a.y > p.y) != (b.y > p.y) && p.x < (b.x - a.x) * (p.y - a.y) / (b.y - a.y) + a.x) c = !c
                j = i
            }
            return c
        }
    }

    /** Рёбра, у которых нет пары — признак незамкнутой модели (0 — всё хорошо). */
    fun openEdges(): Int {
        val directed = HashMap<Long, Int>()
        for (f in faces) for (l in listOf(f.outer) + f.holes) for (k in l.indices) {
            val c = l[k].toLong() shl 32 or l[(k + 1) % l.size].toLong()
            directed[c] = (directed[c] ?: 0) + 1
        }
        return directed.keys.count { c -> val a = (c shr 32).toInt(); val b = c.toInt(); !directed.containsKey(b.toLong() shl 32 or a.toLong()) }
    }
}
