package com.dividinghead.calc

import com.dividinghead.calc.model.Presets
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertThrows
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test

class SimpleIndexingTest {

    private val plateSet = Presets.brownSharpePlateSet

    @Test
    fun `n=1 gives exactly N whole turns and no fraction`() {
        val result = SimpleIndexing.calculate(n = 1, characteristicN = 40, plateSet = plateSet)
        assertEquals(40, result.wholeTurns)
        assertFalse(result.hasFraction)
        assertTrue(result.exact)
        assertEquals(0.0, result.errorArcSeconds)
    }

    @Test
    fun `divisor of N gives exact whole number of turns`() {
        val result = SimpleIndexing.calculate(n = 8, characteristicN = 40, plateSet = plateSet)
        assertEquals(5, result.wholeTurns)
        assertFalse(result.hasFraction)
        assertTrue(result.exact)
    }

    @Test
    fun `classic 6-division example matches textbook solution`() {
        // 40 / 6 = 6 whole turns + 4/6 = 2/3 of a turn -> any circle divisible by 3 works exactly
        // (e.g. 21 holes -> 14 holes step); the solver may pick any of several exact circles.
        val result = SimpleIndexing.calculate(n = 6, characteristicN = 40, plateSet = plateSet)
        assertEquals(6, result.wholeTurns)
        assertTrue(result.exact)
        assertEquals(0, result.circleHoles % 3)
        assertEquals(result.circleHoles * 2 / 3, result.holes)
        assertEquals(0.0, result.errorArcSeconds, 1e-9)
    }

    @Test
    fun `very large n still returns a finite approximate result without exception`() {
        val result = SimpleIndexing.calculate(n = 100_000, characteristicN = 40, plateSet = plateSet)
        assertEquals(0, result.wholeTurns)
        assertTrue(result.circleHoles > 0)
        assertTrue(result.errorArcSeconds.isFinite())
        assertTrue(result.errorPercentOfStep.isFinite())
    }

    @Test
    fun `prime number of divisions with no exact circle is only approximate`() {
        // 127 has no exact solution on the Brown & Sharpe plate set.
        val result = SimpleIndexing.calculate(n = 127, characteristicN = 40, plateSet = plateSet)
        assertFalse(result.exact)
        assertTrue(result.errorArcSeconds > 0.0)
    }

    @Test
    fun `zero or negative divisions are rejected`() {
        assertThrows(IllegalArgumentException::class.java) {
            SimpleIndexing.calculate(n = 0, characteristicN = 40, plateSet = plateSet)
        }
        assertThrows(IllegalArgumentException::class.java) {
            SimpleIndexing.calculate(n = -5, characteristicN = 40, plateSet = plateSet)
        }
    }

    @Test
    fun `custom head characteristic other than 40 is honoured`() {
        val result = SimpleIndexing.calculate(n = 5, characteristicN = 60, plateSet = plateSet)
        assertEquals(12, result.wholeTurns)
        assertTrue(result.exact)
    }
}
