package ru.konstruktor.eskiz.export

import ru.konstruktor.eskiz.geom.Arc
import ru.konstruktor.eskiz.geom.P
import ru.konstruktor.eskiz.render.DrawingModel
import java.util.Locale
import kotlin.math.abs
import kotlin.math.max

/**
 * 3D-модель выдавливанием: замкнутый контур детали (линии и дуги), вырезы и отверстия
 * поднимаются на толщину и записываются твердотельной B-rep моделью в STEP (AP214).
 * Координаты — мм, ось Y вверх (как в CAD).
 */
object Extrusion {

    /** Ребро плоского контура от [p] к [q]; для дуги — центр, радиус и направление обхода. */
    sealed class Edge2 {
        abstract val p: P
        abstract val q: P
        abstract fun reversed(): Edge2
        abstract fun sample(n: Int): List<P>

        data class Line(override val p: P, override val q: P) : Edge2() {
            override fun reversed() = Line(q, p)
            override fun sample(n: Int) = listOf(p, q)
        }

        data class Circ(override val p: P, override val q: P, val c: P, val r: Double, val ccw: Boolean) : Edge2() {
            override fun reversed() = Circ(q, p, c, r, !ccw)
            override fun sample(n: Int): List<P> {
                val tau = 2 * Math.PI
                val a0 = (p - c).angle(); val a1 = (q - c).angle()
                var sw = ((a1 - a0) % tau + tau) % tau
                if (!ccw) sw -= tau
                if (abs(sw) < 1e-12) sw = if (ccw) tau else -tau
                return (0..n).map { val a = a0 + sw * it / n; P(c.x + r * kotlin.math.cos(a), c.y + r * kotlin.math.sin(a)) }
            }
        }
    }

    /** Замкнутый контур: материал детали всегда слева по ходу обхода. */
    class Loop(val edges: List<Edge2>) {
        val polygon get() = edges.flatMap { it.sample(12).dropLast(1) }
        val area: Double get() {
            val pts = polygon
            var s = 0.0
            for (i in pts.indices) { val a = pts[i]; val b = pts[(i + 1) % pts.size]; s += a.x * b.y - b.x * a.y }
            return s / 2
        }
        fun reversed() = Loop(edges.reversed().map { it.reversed() })
    }

    class Profile(val outer: Loop, val inner: List<Loop>)

    class ProfileError(message: String) : Exception(message)

    /** Собирает профиль из чертежа: внешний контур, вырезы (внутренние контуры) и отверстия. */
    fun profile(model: DrawingModel): Profile {
        val project = model.project
        fun pt(id: Int): P { val p = project.point(id) ?: throw ProfileError("Нет точки $id"); return up(model.map(p.p)) }

        class E(val a: Int, val b: Int, val mid: Int?)
        val edges = project.lines.map { E(it.a, it.b, null) } + project.arcs.map { E(it.a, it.b, it.m) }
        if (edges.isEmpty()) throw ProfileError("Нет контура: обведите деталь (инструмент «Авто» или линии)")
        val adj = HashMap<Int, MutableList<Int>>()
        edges.forEachIndexed { i, e -> adj.getOrPut(e.a) { mutableListOf() } += i; adj.getOrPut(e.b) { mutableListOf() } += i }
        val bad = adj.filter { it.value.size != 2 }.keys
        if (bad.isNotEmpty()) throw ProfileError("Контур не замкнут или ветвится (точек с ошибкой: ${bad.size}). Каждая точка контура должна соединять ровно две линии.")

        val used = BooleanArray(edges.size)
        val loops = ArrayList<Loop>()
        for (start in edges.indices) {
            if (used[start]) continue
            val list = ArrayList<Edge2>()
            var cur = start
            var from = edges[start].a
            while (!used[cur]) {
                used[cur] = true
                val e = edges[cur]
                val to = if (e.a == from) e.b else e.a
                list += if (e.mid == null) Edge2.Line(pt(from), pt(to)) else {
                    val arc = Arc.through(pt(e.a), pt(e.mid), pt(e.b)) ?: throw ProfileError("Дуга вырождена в прямую")
                    val ccwAB = arc.sweep > 0
                    Edge2.Circ(pt(from), pt(to), arc.c, arc.r, if (from == e.a) ccwAB else !ccwAB)
                }
                from = to
                cur = adj[to]!!.firstOrNull { it != cur && !used[it] } ?: break
            }
            if (list.size < 2 && list.none { it is Edge2.Circ }) throw ProfileError("Слишком маленький контур")
            loops += Loop(list)
        }
        val outer0 = loops.maxByOrNull { abs(it.area) }!!
        val outer = if (outer0.area > 0) outer0 else outer0.reversed()
        val outerPoly = outer.polygon
        val inner = ArrayList<Loop>()
        for (l in loops) {
            if (l === outer0) continue
            if (!inside(l.polygon[0], outerPoly)) throw ProfileError("Несколько отдельных контуров — оставьте один (деталь) и вырезы внутри него")
            inner += if (l.area < 0) l else l.reversed()
        }
        for (c in model.circles) {
            val cc = up(c.circle.c); val r = c.circle.r
            if (!inside(cc, outerPoly)) continue
            val p0 = P(cc.x + r, cc.y); val p1 = P(cc.x - r, cc.y)
            inner += Loop(listOf(Edge2.Circ(p0, p1, cc, r, false), Edge2.Circ(p1, p0, cc, r, false)))
        }
        return Profile(outer, inner)
    }

    private fun up(p: P) = P(p.x, -p.y)

    private fun inside(p: P, poly: List<P>): Boolean {
        var c = false
        var j = poly.size - 1
        for (i in poly.indices) {
            val a = poly[i]; val b = poly[j]
            if ((a.y > p.y) != (b.y > p.y) && p.x < (b.x - a.x) * (p.y - a.y) / (b.y - a.y) + a.x) c = !c
            j = i
        }
        return c
    }

    /** Текст STEP-файла: тело выдавливания профиля на [thickness] мм. */
    fun step(profile: Profile, thickness: Double, name: String): String {
        val w = StepWriter()
        val t = thickness
        val zUp = w.dir(0.0, 0.0, 1.0); val xDir = w.dir(1.0, 0.0, 0.0)
        val faces = ArrayList<Int>()

        class Built(val top: List<Int>, val bottom: List<Int>)
        fun build(loop: Loop): Built {
            val n = loop.edges.size
            val vb = loop.edges.map { w.vertex(it.p, 0.0) }
            val vt = loop.edges.map { w.vertex(it.p, t) }
            val vertical = (0 until n).map { i -> w.lineEdge(vb[i], vt[i], loop.edges[i].p, 0.0, loop.edges[i].p, t) }
            val bottom = ArrayList<Int>(); val top = ArrayList<Int>()
            for (i in 0 until n) {
                val e = loop.edges[i]; val j = (i + 1) % n
                bottom += w.edge(e, vb[i], vb[j], 0.0)
                top += w.edge(e, vt[i], vt[j], t)
                // Боковая грань: снизу p→q, вверх в q, сверху q→p, вниз в p.
                val bound = w.loop(listOf(w.oe(bottom[i], true), w.oe(vertical[j], true), w.oe(top[i], false), w.oe(vertical[i], false)))
                val surface: Int; val sense: Boolean
                when (e) {
                    is Edge2.Line -> {
                        val d = (e.q - e.p).norm()
                        surface = w.add("PLANE('',${w.axis(e.p, 0.0, w.dir(d.y, -d.x, 0.0), w.dir(d.x, d.y, 0.0))})")
                        sense = true
                    }
                    is Extrusion.Edge2.Circ -> {
                        surface = w.add("CYLINDRICAL_SURFACE('',${w.axis(e.c, 0.0, zUp, xDir)},${w.f(e.r)})")
                        sense = e.ccw
                    }
                }
                faces += w.add("ADVANCED_FACE('',(#${w.add("FACE_OUTER_BOUND('',$bound,.T.)")}),#$surface,${w.b(sense)})")
            }
            return Built(top, bottom)
        }

        val all = listOf(profile.outer) + profile.inner
        val built = all.map(::build)
        // Верх (нормаль +Z): контуры в своём направлении.
        val topBounds = built.mapIndexed { i, b ->
            val l = w.loop(b.top.map { w.oe(it, true) })
            w.add(if (i == 0) "FACE_OUTER_BOUND('',$l,.T.)" else "FACE_BOUND('',$l,.T.)")
        }
        faces += w.add("ADVANCED_FACE('',(${topBounds.joinToString(",") { "#$it" }}),#${w.add("PLANE('',${w.axis(P(0.0, 0.0), t, zUp, xDir)})")},.T.)")
        // Низ (нормаль −Z): контуры в обратном направлении.
        val bottomBounds = built.mapIndexed { i, b ->
            val l = w.loop(b.bottom.reversed().map { w.oe(it, false) })
            w.add(if (i == 0) "FACE_OUTER_BOUND('',$l,.T.)" else "FACE_BOUND('',$l,.T.)")
        }
        faces += w.add("ADVANCED_FACE('',(${bottomBounds.joinToString(",") { "#$it" }}),#${w.add("PLANE('',${w.axis(P(0.0, 0.0), 0.0, w.dir(0.0, 0.0, -1.0), xDir)})")},.T.)")

        val shell = w.add("CLOSED_SHELL('',(${faces.joinToString(",") { "#$it" }}))")
        val brep = w.add("MANIFOLD_SOLID_BREP('${ascii(name)}',#$shell)")
        return w.document(brep, ascii(name))
    }

    /** STEP допускает только ASCII в строках: русские буквы переводим латиницей. */
    fun ascii(s: String): String {
        val map = mapOf('а' to "a", 'б' to "b", 'в' to "v", 'г' to "g", 'д' to "d", 'е' to "e", 'ё' to "e", 'ж' to "zh",
            'з' to "z", 'и' to "i", 'й' to "y", 'к' to "k", 'л' to "l", 'м' to "m", 'н' to "n", 'о' to "o", 'п' to "p",
            'р' to "r", 'с' to "s", 'т' to "t", 'у' to "u", 'ф' to "f", 'х' to "h", 'ц' to "ts", 'ч' to "ch", 'ш' to "sh",
            'щ' to "sch", 'ъ' to "", 'ы' to "y", 'ь' to "", 'э' to "e", 'ю' to "yu", 'я' to "ya")
        val sb = StringBuilder()
        for (ch in s) {
            val low = ch.lowercaseChar()
            val tr = map[low]
            when {
                tr != null -> sb.append(if (ch.isUpperCase()) tr.replaceFirstChar { it.uppercaseChar() } else tr)
                ch.code in 32..126 && ch != '\'' && ch != '\\' -> sb.append(ch)
                else -> sb.append('_')
            }
        }
        return sb.toString().ifBlank { "Part" }
    }
}

/** Запись сущностей STEP (AP214) с автонумерацией. */
internal class StepWriter {
    private val sb = StringBuilder()
    private var n = 100

    /** Число STEP: 10 знаков (иначе вершины «не ложатся» на кривые в пределах допуска), без лишних нулей. */
    fun f(v: Double): String =
        String.format(Locale.US, "%.10f", if (abs(v) < 1e-13) 0.0 else v).trimEnd('0')
    fun b(v: Boolean) = if (v) ".T." else ".F."

    fun add(e: String): Int { val id = n++; sb.append('#').append(id).append('=').append(e).append(";\n"); return id }
    private fun ref(id: Int) = "#$id"

    fun point(x: Double, y: Double, z: Double) = add("CARTESIAN_POINT('',(${f(x)},${f(y)},${f(z)}))")
    fun dir(x: Double, y: Double, z: Double): Int {
        val l = max(1e-15, kotlin.math.sqrt(x * x + y * y + z * z))
        return add("DIRECTION('',(${f(x / l)},${f(y / l)},${f(z / l)}))")
    }
    fun axis(p: P, z: Double, axisDir: Int, refDir: Int) = ref(add("AXIS2_PLACEMENT_3D('',${ref(point(p.x, p.y, z))},${ref(axisDir)},${ref(refDir)})"))
    fun vertex(p: P, z: Double) = add("VERTEX_POINT('',${ref(point(p.x, p.y, z))})")

    fun lineEdge(v1: Int, v2: Int, a: P, za: Double, b: P, zb: Double): Int {
        val dx = b.x - a.x; val dy = b.y - a.y; val dz = zb - za
        val len = kotlin.math.sqrt(dx * dx + dy * dy + dz * dz)
        val line = add("LINE('',${ref(point(a.x, a.y, za))},${ref(add("VECTOR('',${ref(dir(dx, dy, dz))},${f(len)})"))})")
        return add("EDGE_CURVE('',${ref(v1)},${ref(v2)},${ref(line)},.T.)")
    }

    fun edge(e: Extrusion.Edge2, v1: Int, v2: Int, z: Double): Int = when (e) {
        is Extrusion.Edge2.Line -> lineEdge(v1, v2, e.p, z, e.q, z)
        is Extrusion.Edge2.Circ -> {
            val circle = add("CIRCLE('',${axis(e.c, z, dir(0.0, 0.0, 1.0), dir(1.0, 0.0, 0.0))},${f(e.r)})")
            add("EDGE_CURVE('',${ref(v1)},${ref(v2)},${ref(circle)},${b(e.ccw)})")
        }
    }

    fun oe(edge: Int, sense: Boolean) = add("ORIENTED_EDGE('',*,*,${ref(edge)},${b(sense)})")
    fun loop(oes: List<Int>) = ref(add("EDGE_LOOP('',(${oes.joinToString(",") { ref(it) }}))"))

    fun document(brep: Int, name: String): String {
        val head = """ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('Eskiz extrusion'),'2;1');
FILE_NAME('$name.step','2026-01-01T00:00:00',(''),(''),'Eskiz','Eskiz','');
FILE_SCHEMA(('AUTOMOTIVE_DESIGN { 1 0 10303 214 1 1 1 1 }'));
ENDSEC;
DATA;
#1=APPLICATION_CONTEXT('automotive design');
#2=APPLICATION_PROTOCOL_DEFINITION('international standard','automotive_design',2000,#1);
#3=PRODUCT_CONTEXT('',#1,'mechanical');
#4=PRODUCT('$name','$name','',(#3));
#5=PRODUCT_DEFINITION_FORMATION('','',#4);
#6=PRODUCT_DEFINITION_CONTEXT('part definition',#1,'design');
#7=PRODUCT_DEFINITION('design','',#5,#6);
#8=PRODUCT_DEFINITION_SHAPE('','',#7);
#9=(LENGTH_UNIT()NAMED_UNIT(*)SI_UNIT(.MILLI.,.METRE.));
#10=(NAMED_UNIT(*)PLANE_ANGLE_UNIT()SI_UNIT(${'$'},.RADIAN.));
#11=(NAMED_UNIT(*)SI_UNIT(${'$'},.STERADIAN.)SOLID_ANGLE_UNIT());
#12=UNCERTAINTY_MEASURE_WITH_UNIT(LENGTH_MEASURE(1.E-06),#9,'distance_accuracy_value','confusion accuracy');
#13=(GEOMETRIC_REPRESENTATION_CONTEXT(3)GLOBAL_UNCERTAINTY_ASSIGNED_CONTEXT((#12))GLOBAL_UNIT_ASSIGNED_CONTEXT((#9,#10,#11))REPRESENTATION_CONTEXT('Context3D','3D Context with UNIT and UNCERTAINTY'));
#14=PRODUCT_RELATED_PRODUCT_CATEGORY('part',${'$'},(#4));
"""
        val origin = add("AXIS2_PLACEMENT_3D('',${ref(point(0.0, 0.0, 0.0))},${ref(dir(0.0, 0.0, 1.0))},${ref(dir(1.0, 0.0, 0.0))})")
        val rep = add("ADVANCED_BREP_SHAPE_REPRESENTATION('',(#$brep,#$origin),#13)")
        add("SHAPE_DEFINITION_REPRESENTATION(#8,#$rep)")
        return head + sb + "ENDSEC;\nEND-ISO-10303-21;\n"
    }
}
