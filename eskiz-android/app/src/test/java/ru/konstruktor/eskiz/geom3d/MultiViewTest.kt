package ru.konstruktor.eskiz.geom3d

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import ru.konstruktor.eskiz.export.Extrusion
import ru.konstruktor.eskiz.export.Extrusion.Edge2
import ru.konstruktor.eskiz.export.SolidExport
import ru.konstruktor.eskiz.geom.P
import java.io.File
import kotlin.math.PI

class MultiViewTest {
    private val out = File("build/multiview-test").apply { mkdirs() }

    private fun poly(vararg xy: Double): Extrusion.Loop {
        val pts = (xy.indices step 2).map { P(xy[it], xy[it + 1]) }
        return Extrusion.Loop(pts.indices.map { Edge2.Line(pts[it], pts[(it + 1) % pts.size]) })
    }

    /** Отверстие: две полуокружности по часовой (материал слева). */
    private fun hole(cx: Double, cy: Double, r: Double): Extrusion.Loop {
        val c = P(cx, cy); val p0 = P(cx + r, cy); val p1 = P(cx - r, cy)
        return Extrusion.Loop(listOf(Edge2.Circ(p0, p1, c, r, false), Edge2.Circ(p1, p0, c, r, false)))
    }

    private fun save(name: String, r: MultiView.Result) {
        File(out, "$name.step").writeText(SolidExport.step(r.solid, name))
        File(out, "$name.stl").writeBytes(SolidExport.stl(r.solid, name))
        val w = 640; val h = 480
        val px = Preview.render(r.solid, w, h, Math.toRadians(-35.0), Math.toRadians(25.0), 0xFFFFFFFF.toInt())
        Png.write(File(out, "$name.png"), px, w, h)
    }

    @Test
    fun singleViewPlate() {
        val plate = Extrusion.Profile(poly(0.0, 0.0, 100.0, 0.0, 100.0, 50.0, 0.0, 50.0), listOf(hole(30.0, 25.0, 10.0)))
        val r = MultiView.build(listOf(MultiView.View(MultiView.Role.TOP, plate)), thickness = 8.0)
        val expected = (5000 - PI * 100) * 8
        println("Пластина: объём ${r.solid.volume} (ожид. $expected), граней ${r.solid.faces.size}, размер ${r.size}")
        assertEquals(0, r.solid.openEdges())
        assertEquals(expected, r.solid.volume, expected * 0.002)
        save("plate", r)
    }

    @Test
    fun bracketFromThreeViews() {
        // Спереди: L-профиль (ширина 100, высота 60, полки 10 мм).
        val front = Extrusion.Profile(poly(0.0, 0.0, 100.0, 0.0, 100.0, 10.0, 10.0, 10.0, 10.0, 60.0, 0.0, 60.0), emptyList())
        // Сверху: 100 × 40 с отверстием Ø12 в основании.
        val top = Extrusion.Profile(poly(0.0, 0.0, 100.0, 0.0, 100.0, 40.0, 0.0, 40.0), listOf(hole(60.0, 20.0, 6.0)))
        // Слева: 40 × 60 с отверстием Ø10 в стенке.
        val left = Extrusion.Profile(poly(0.0, 0.0, 40.0, 0.0, 40.0, 60.0, 0.0, 60.0), listOf(hole(20.0, 40.0, 5.0)))
        val t0 = System.currentTimeMillis()
        val r = MultiView.build(listOf(
            MultiView.View(MultiView.Role.FRONT, front),
            MultiView.View(MultiView.Role.TOP, top),
            MultiView.View(MultiView.Role.LEFT, left),
        ))
        val expected = 1500.0 * 40 - PI * 36 * 10 - PI * 25 * 10
        println("Кронштейн за ${System.currentTimeMillis() - t0} мс: объём ${r.solid.volume} (ожид. $expected), граней ${r.solid.faces.size}, " +
            "вершин ${r.solid.vertices.size}, размер ${r.size}, предупреждения ${r.warnings}")
        assertEquals(0, r.solid.openEdges())
        assertTrue(r.warnings.isEmpty())
        assertEquals(expected, r.solid.volume, expected * 0.003)
        assertEquals(100.0, r.size.x, 1e-6); assertEquals(40.0, r.size.y, 1e-6); assertEquals(60.0, r.size.z, 1e-6)
        save("bracket", r)
    }

    @Test
    fun lugWithArcSlotAndTee() {
        // Спереди: проушина — прямоугольник 80×50 со скруглённым верхом R40 и отверстием Ø20 в центре скругления.
        val c = P(40.0, 50.0)
        val front = Extrusion.Profile(
            Extrusion.Loop(listOf(
                Edge2.Line(P(0.0, 0.0), P(80.0, 0.0)),
                Edge2.Line(P(80.0, 0.0), P(80.0, 50.0)),
                Edge2.Circ(P(80.0, 50.0), P(0.0, 50.0), c, 40.0, true),
                Edge2.Line(P(0.0, 50.0), P(0.0, 0.0)),
            )),
            listOf(hole(40.0, 50.0, 10.0)),
        )
        // Сверху: 80.4 × 60 (на 0,5% шире — должно подогнаться) с пазом 30×8.
        val top = Extrusion.Profile(poly(0.0, 0.0, 80.4, 0.0, 80.4, 60.0, 0.0, 60.0), listOf(poly(25.0, 10.0, 55.0, 10.0, 55.0, 18.0, 25.0, 18.0).let {
            Extrusion.Loop(it.edges.reversed().map { e -> e.reversed() })
        }))
        // Справа: Т-образный — основание 60 × 12, стойка 20 мм посередине до высоты 90.
        val right = Extrusion.Profile(poly(0.0, 0.0, 60.0, 0.0, 60.0, 12.0, 40.0, 12.0, 40.0, 90.0, 20.0, 90.0, 20.0, 12.0, 0.0, 12.0), emptyList())
        val r = MultiView.build(listOf(
            MultiView.View(MultiView.Role.FRONT, front),
            MultiView.View(MultiView.Role.TOP, top),
            MultiView.View(MultiView.Role.RIGHT, right),
        ))
        println("Проушина: объём ${r.solid.volume}, граней ${r.solid.faces.size}, размер ${r.size}, открытых рёбер ${r.solid.openEdges()}, ${r.warnings}")
        assertEquals(0, r.solid.openEdges())
        assertEquals(80.2, r.size.x, 1e-6); assertEquals(90.0, r.size.z, 1e-6)
        save("lug", r)
    }

    @Test
    fun mismatchedViewsAreReported() {
        val front = Extrusion.Profile(poly(0.0, 0.0, 100.0, 0.0, 100.0, 30.0, 0.0, 30.0), emptyList())
        val top = Extrusion.Profile(poly(0.0, 0.0, 99.0, 0.0, 99.0, 40.0, 0.0, 40.0), emptyList())   // 1% — подгоняется
        val r = MultiView.build(listOf(MultiView.View(MultiView.Role.FRONT, front), MultiView.View(MultiView.Role.TOP, top)))
        assertTrue(r.warnings.isEmpty())
        assertEquals(99.5, r.size.x, 1e-6)
        val top2 = Extrusion.Profile(poly(0.0, 0.0, 80.0, 0.0, 80.0, 40.0, 0.0, 40.0), emptyList())  // 20% — предупреждение
        val r2 = MultiView.build(listOf(MultiView.View(MultiView.Role.FRONT, front), MultiView.View(MultiView.Role.TOP, top2)))
        println(r2.warnings)
        assertTrue(r2.warnings.any { it.contains("ширина") })
    }
}
