package com.dividinghead.calc

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test

class GearCombinationSearchTest {

    @Test
    fun `empty gear list yields no combinations`() {
        val result = GearCombinationSearch.findBestCombinations(Fraction.of(1, 3), emptyList())
        assertTrue(result.isEmpty())
    }

    @Test
    fun `exact single pair ratio is found and marked exact`() {
        val gears = listOf(24, 28, 32, 40, 44, 48, 56, 64, 72, 86, 100)
        val result = GearCombinationSearch.findBestCombinations(Fraction.of(4, 3), gears, maxResults = 3)
        assertTrue(result.isNotEmpty())
        assertTrue(result.first().exact)
        assertEquals(0.0, result.first().errorPercent, 1e-9)
    }

    @Test
    fun `results are sorted by ascending absolute error`() {
        val gears = listOf(20, 24, 28, 32, 40, 48, 60, 72, 100)
        val result = GearCombinationSearch.findBestCombinations(Fraction.of(7, 3), gears, maxResults = 10)
        val errors = result.map { kotlin.math.abs(it.errorPercent) }
        assertEquals(errors.sorted(), errors)
    }

    @Test
    fun `infeasible compound trains are always ranked after feasible ones`() {
        val gears = listOf(24, 100)
        val result = GearCombinationSearch.findBestCombinations(Fraction.of(17, 4), gears, maxResults = 20)
        val firstInfeasibleIndex = result.indexOfFirst { !it.feasible }
        val lastFeasibleIndex = result.indexOfLast { it.feasible }
        if (firstInfeasibleIndex != -1 && lastFeasibleIndex != -1) {
            assertTrue(lastFeasibleIndex < firstInfeasibleIndex)
        }
    }
}
