package ru.konstruktor.eskiz.geom3d

import kotlin.math.sqrt

data class V3(val x: Double, val y: Double, val z: Double) {
    operator fun plus(o: V3) = V3(x + o.x, y + o.y, z + o.z)
    operator fun minus(o: V3) = V3(x - o.x, y - o.y, z - o.z)
    operator fun times(k: Double) = V3(x * k, y * k, z * k)
    operator fun unaryMinus() = V3(-x, -y, -z)
    fun dot(o: V3) = x * o.x + y * o.y + z * o.z
    fun cross(o: V3) = V3(y * o.z - z * o.y, z * o.x - x * o.z, x * o.y - y * o.x)
    fun len() = sqrt(dot(this))
    fun unit(): V3 { val l = len(); return if (l < 1e-300) this else this * (1 / l) }
    fun lerp(o: V3, t: Double) = this + (o - this) * t
    operator fun get(i: Int) = when (i) { 0 -> x; 1 -> y; else -> z }
}

/**
 * Булевы операции над замкнутыми многогранниками на BSP-деревьях (по мотивам csg.js).
 * Многоугольники выпуклые, нормаль наружу (обход против часовой, если смотреть снаружи).
 */
object Csg {
    const val EPS = 1e-5

    class Plane(val n: V3, val w: Double) {
        fun flipped() = Plane(-n, -w)

        companion object {
            fun of(a: V3, b: V3, c: V3): Plane {
                val n = (b - a).cross(c - a).unit()
                return Plane(n, n.dot(a))
            }
        }

        private val coplanar = 0
        private val front = 1
        private val back = 2
        private val spanning = 3

        fun split(
            poly: Poly, coplanarFront: MutableList<Poly>, coplanarBack: MutableList<Poly>,
            frontList: MutableList<Poly>, backList: MutableList<Poly>,
        ) {
            var polyType = 0
            val types = IntArray(poly.v.size)
            for ((i, v) in poly.v.withIndex()) {
                val t = n.dot(v) - w
                val type = if (t < -EPS) back else if (t > EPS) front else coplanar
                polyType = polyType or type
                types[i] = type
            }
            when (polyType) {
                coplanar -> (if (n.dot(poly.plane.n) > 0) coplanarFront else coplanarBack).add(poly)
                front -> frontList.add(poly)
                back -> backList.add(poly)
                else -> {
                    val f = ArrayList<V3>(); val b = ArrayList<V3>()
                    val cnt = poly.v.size
                    for (i in 0 until cnt) {
                        val j = (i + 1) % cnt
                        val ti = types[i]; val tj = types[j]
                        val vi = poly.v[i]; val vj = poly.v[j]
                        if (ti != back) f += vi
                        if (ti != front) b += vi
                        if ((ti or tj) == spanning) {
                            val t = (w - n.dot(vi)) / n.dot(vj - vi)
                            val v = vi.lerp(vj, t)
                            f += v; b += v
                        }
                    }
                    if (f.size >= 3) frontList.add(Poly(f, poly.plane))
                    if (b.size >= 3) backList.add(Poly(b, poly.plane))
                }
            }
        }
    }

    class Poly(val v: List<V3>, val plane: Plane = Plane.of(v[0], v[1], v[2])) {
        fun flipped() = Poly(v.reversed(), plane.flipped())
    }

    private class Node(polys: List<Poly>? = null) {
        var plane: Plane? = null
        var front: Node? = null
        var back: Node? = null
        var polygons = ArrayList<Poly>()

        init { if (polys != null) build(polys) }

        fun invert() {
            polygons = ArrayList(polygons.map { it.flipped() })
            plane = plane?.flipped()
            front?.invert(); back?.invert()
            val t = front; front = back; back = t
        }

        fun clipPolygons(polys: List<Poly>): List<Poly> {
            val p = plane ?: return ArrayList(polys)
            val f = ArrayList<Poly>(); val b = ArrayList<Poly>()
            for (poly in polys) p.split(poly, f, b, f, b)
            val ff = front?.clipPolygons(f) ?: f
            val bb = back?.clipPolygons(b) ?: emptyList()
            return ff + bb
        }

        fun clipTo(bsp: Node) {
            polygons = ArrayList(bsp.clipPolygons(polygons))
            front?.clipTo(bsp); back?.clipTo(bsp)
        }

        fun allPolygons(): List<Poly> {
            val out = ArrayList<Poly>(polygons)
            front?.let { out += it.allPolygons() }
            back?.let { out += it.allPolygons() }
            return out
        }

        fun build(polys: List<Poly>) {
            if (polys.isEmpty()) return
            val p = plane ?: polys[0].plane.also { plane = it }
            val f = ArrayList<Poly>(); val b = ArrayList<Poly>()
            for (poly in polys) p.split(poly, polygons, polygons, f, b)
            if (f.isNotEmpty()) (front ?: Node().also { front = it }).build(f)
            if (b.isNotEmpty()) (back ?: Node().also { back = it }).build(b)
        }
    }

    fun intersect(a: List<Poly>, b: List<Poly>): List<Poly> = deep {
        val na = Node(a); val nb = Node(b)
        na.invert(); nb.clipTo(na); nb.invert(); na.clipTo(nb); nb.clipTo(na)
        na.build(nb.allPolygons()); na.invert()
        na.allPolygons()
    }

    fun subtract(a: List<Poly>, b: List<Poly>): List<Poly> = deep {
        val na = Node(a); val nb = Node(b)
        na.invert(); na.clipTo(nb); nb.clipTo(na); nb.invert(); nb.clipTo(na); nb.invert()
        na.build(nb.allPolygons()); na.invert()
        na.allPolygons()
    }

    /** BSP-деревья рекурсивны: считаем в потоке с большим стеком. */
    private fun <T> deep(block: () -> T): T {
        var result: Result<T>? = null
        val t = Thread(null, { result = runCatching(block) }, "csg", 256L * 1024 * 1024)
        t.start(); t.join()
        return result!!.getOrThrow()
    }
}
