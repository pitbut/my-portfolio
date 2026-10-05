package ru.konstruktor.eskiz.export

import ru.konstruktor.eskiz.geom.P
import ru.konstruktor.eskiz.geom3d.Solid
import java.nio.ByteBuffer
import java.nio.ByteOrder

/** Запись многогранной модели (3D по нескольким видам) в STEP и STL. */
object SolidExport {

    /** STEP AP214: твёрдое тело из плоских граней (отверстия — многогранные). */
    fun step(s: Solid, name: String): String {
        val w = StepWriter()
        val vid = s.vertices.map { w.vertex(P(it.x, it.y), it.z) }
        val edges = HashMap<Long, Int>()
        fun oe(a: Int, b: Int): Int {
            val lo = minOf(a, b); val hi = maxOf(a, b)
            val e = edges.getOrPut(lo.toLong() shl 32 or hi.toLong()) {
                val p = s.vertices[lo]; val q = s.vertices[hi]
                w.lineEdge(vid[lo], vid[hi], P(p.x, p.y), p.z, P(q.x, q.y), q.z)
            }
            return w.oe(e, a == lo)
        }
        val faces = s.faces.map { f ->
            fun loop(l: IntArray) = w.loop(l.indices.map { k -> oe(l[k], l[(k + 1) % l.size]) })
            val bounds = listOf(w.add("FACE_OUTER_BOUND('',${loop(f.outer)},.T.)")) +
                f.holes.map { w.add("FACE_BOUND('',${loop(it)},.T.)") }
            val (u, _) = Solid.basis(f.normal)
            val o = s.vertices[f.outer[0]]
            val plane = w.add("PLANE('',${w.axis(P(o.x, o.y), o.z, w.dir(f.normal.x, f.normal.y, f.normal.z), w.dir(u.x, u.y, u.z))})")
            w.add("ADVANCED_FACE('',(${bounds.joinToString(",") { "#$it" }}),#$plane,.T.)")
        }
        val shell = w.add("CLOSED_SHELL('',(${faces.joinToString(",") { "#$it" }}))")
        val n = Extrusion.ascii(name)
        val brep = w.add("MANIFOLD_SOLID_BREP('$n',#$shell)")
        return w.document(brep, n)
    }

    /** Двоичный STL (мм) — для 3D-печати и любых просмотрщиков. */
    fun stl(s: Solid, name: String): ByteArray {
        val tris = s.triangles
        val buf = ByteBuffer.allocate(84 + tris.size * 50).order(ByteOrder.LITTLE_ENDIAN)
        val head = "Eskiz ${Extrusion.ascii(name)}".toByteArray().copyOf(80)
        buf.put(head)
        buf.putInt(tris.size)
        for (t in tris) {
            val a = s.vertices[t[0]]; val b = s.vertices[t[1]]; val c = s.vertices[t[2]]
            val n = (b - a).cross(c - a).unit()
            for (v in listOf(n, a, b, c)) { buf.putFloat(v.x.toFloat()); buf.putFloat(v.y.toFloat()); buf.putFloat(v.z.toFloat()) }
            buf.putShort(0)
        }
        return buf.array()
    }
}
