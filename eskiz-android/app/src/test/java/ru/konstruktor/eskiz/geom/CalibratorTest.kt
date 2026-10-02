package ru.konstruktor.eskiz.geom

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import kotlin.math.abs

class CalibratorTest {
    // «Истинная» камера: деталь 400×250 мм снята под заметным углом.
    private val worldToImage: Mat3 = run {
        val k = Mat3(doubleArrayOf(6.0, 0.4, 600.0, -0.3, 5.2, 500.0, 0.0006, 0.0004, 1.0))
        k
    }
    private val imageToWorld = worldToImage.inverse()
    private fun img(x: Double, y: Double) = worldToImage.apply(P(x, y))

    private val corners = listOf(P(0.0, 0.0), P(400.0, 0.0), P(400.0, 250.0), P(0.0, 250.0), P(200.0, 120.0), P(80.0, 200.0))

    private fun constraint(id: Int, a: P, b: P, err: Double = 0.0) =
        LinearConstraint(id, img(a.x, a.y), img(b.x, b.y), dist(a, b) + err)

    private fun checkDist(c: Calibration, a: P, b: P, tolRel: Double) {
        val got = dist(c.toMm(img(a.x, a.y)), c.toMm(img(b.x, b.y)))
        val want = dist(a, b)
        assertTrue("got $got want $want", abs(got - want) / want < tolRel)
    }

    @Test
    fun fullPerspectiveRecovered() {
        val cs = listOf(
            constraint(1, corners[0], corners[1]),
            constraint(2, corners[1], corners[2]),
            constraint(3, corners[2], corners[3]),
            constraint(4, corners[3], corners[0]),
            constraint(5, corners[0], corners[2]),
            constraint(6, corners[4], corners[5]),
        )
        val c = Calibrator.calibrate(1600, 1200, null, cs)
        assertEquals(CalibMode.FULL, c.mode)
        assertTrue(c.outliers.isEmpty())
        checkDist(c, corners[1], corners[3], 0.002)
        checkDist(c, P(50.0, 30.0), P(350.0, 220.0), 0.002)
        checkDist(c, P(300.0, 10.0), P(310.0, 240.0), 0.003)
    }

    @Test
    fun typoIsFlagged() {
        val cs = listOf(
            constraint(1, corners[0], corners[1]),
            constraint(2, corners[1], corners[2]),
            constraint(3, corners[2], corners[3]),
            constraint(4, corners[3], corners[0]),
            constraint(5, corners[0], corners[2]),
            constraint(6, corners[4], corners[5]),
            constraint(7, corners[1], corners[5], err = 9.0 * 4), // опечатка
        )
        val c = Calibrator.calibrate(1600, 1200, null, cs)
        assertEquals(setOf(7), c.outliers.keys)
        checkDist(c, corners[1], corners[3], 0.003)
    }

    @Test
    fun singleDimensionGivesScale() {
        val c = Calibrator.calibrate(1600, 1200, null, listOf(constraint(1, corners[0], corners[1])))
        assertEquals(CalibMode.SCALE, c.mode)
        checkDist(c, corners[0], corners[1], 1e-6)
    }

    @Test
    fun sheetOnly() {
        val c = Calibrator.calibrate(1600, 1200, imageToWorld, emptyList())
        assertTrue(c.calibrated)
        checkDist(c, corners[0], corners[2], 1e-6)
    }

    @Test
    fun sidesOnlyAreHonestlyUncertain() {
        // Только стороны прямоугольника: форма может «перекоситься» — погрешность диагонали большая.
        val sides = listOf(
            constraint(1, corners[0], corners[1]),
            constraint(2, corners[1], corners[2]),
            constraint(3, corners[2], corners[3]),
            constraint(4, corners[3], corners[0]),
        )
        val c1 = Calibrator.calibrate(1600, 1200, null, sides)
        val u1 = c1.uncertainty(img(0.0, 0.0), img(400.0, 250.0))!!
        assertTrue("u1=$u1", u1 > 5.0)
        // С диагоналями — маленькая, и реальная ошибка в её пределах.
        val c2 = Calibrator.calibrate(1600, 1200, null, sides + constraint(5, corners[0], corners[2]) + constraint(6, corners[4], corners[5]))
        val u2 = c2.uncertainty(img(400.0, 0.0), img(0.0, 250.0))!!
        assertTrue("u2=$u2", u2 < 1.5)
        checkDist(c2, corners[1], corners[3], 0.003)
    }

    @Test
    fun circleFit() {
        val pts = (0 until 8).map { P(10 + 5 * kotlin.math.cos(it * 0.7), -3 + 5 * kotlin.math.sin(it * 0.7)) }
        val c = fitCircle(pts)!!
        assertEquals(10.0, c.c.x, 1e-9); assertEquals(-3.0, c.c.y, 1e-9); assertEquals(5.0, c.r, 1e-9)
    }
}
