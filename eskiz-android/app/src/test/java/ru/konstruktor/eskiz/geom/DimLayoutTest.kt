package ru.konstruktor.eskiz.geom

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class DimLayoutTest {
    private val params = DimLayout.Params(textH = 10.0, gap = 20.0, step = 18.0, arrow = 8.0, measure = { it.length * 6.0 })

    // Прямоугольная пластина 300×100 (ось Y вниз).
    private val rect = listOf(P(0.0, 0.0), P(300.0, 0.0), P(300.0, 100.0), P(0.0, 100.0))
    private val geometry = rect.indices.map { rect[it] to rect[(it + 1) % 4] }

    @Test
    fun dimensionsGoOutsideAndDoNotOverlap() {
        val dims = listOf(
            DimLayout.LinearIn(1, P(0.0, 100.0), P(300.0, 100.0), "300"),
            DimLayout.LinearIn(2, P(0.0, 100.0), P(100.0, 100.0), "100"),
            DimLayout.LinearIn(3, P(100.0, 100.0), P(300.0, 100.0), "200"),
            DimLayout.LinearIn(4, P(300.0, 0.0), P(300.0, 100.0), "100"),
        )
        val r = DimLayout.layout(geometry, emptyList(), dims, emptyList(), params)
        val byId = r.linear.associateBy { it.id }
        // Нижние размеры ниже детали.
        for (id in 1..3) assertTrue(byId[id]!!.da.y > 100.0)
        // Цепочка 100 + 200 на одном уровне, габарит 300 — дальше.
        assertEquals(byId[2]!!.da.y, byId[3]!!.da.y, 1e-6)
        assertTrue(byId[1]!!.da.y > byId[2]!!.da.y)
        // Вертикальный — справа.
        assertTrue(byId[4]!!.da.x > 300.0)
        // Тексты не пересекаются.
        val rects = r.linear.map { DimLayout.ORect(it.textCenter, P(kotlin.math.cos(it.textAngle), kotlin.math.sin(it.textAngle)), it.text.length * 3.0, 5.0) }
        for (i in rects.indices) for (j in i + 1 until rects.size) assertFalse(rects[i].intersects(rects[j]))
    }

    @Test
    fun readableDirection() {
        val a = DimLayout.readable(P(-1.0, 0.0))
        assertEquals(1.0, a.x, 1e-12); assertEquals(0.0, a.y, 1e-12)
        val b = DimLayout.readable(P(0.0, 1.0))
        assertEquals(0.0, b.x, 1e-12); assertEquals(-1.0, b.y, 1e-12)
    }
}
