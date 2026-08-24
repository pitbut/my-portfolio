package com.dividinghead.calc

import com.dividinghead.calc.model.GearSet
import com.dividinghead.calc.model.Presets
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertNotNull
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Assertions.assertThrows
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test

class HelicalIndexingTest {

    private val gearSet = Presets.brownSharpeGearSet

    @Test
    fun `lead of 180mm with N=40 Pv=6 yields exact 4-3 gear ratio`() {
        // i = N*Pv/T = 40*6/180 = 4/3 -> achievable exactly with 32/24 from Brown & Sharpe set.
        val result = HelicalIndexing.calculate(
            requiredLeadMm = 180.0,
            leadScrewPitchMm = 6.0,
            characteristicN = 40,
            gearSet = gearSet
        )
        assertTrue(result.gearChoices.isNotEmpty())
        val best = result.gearChoices.first()
        assertTrue(best.exact)
        assertEquals(0.0, result.bestLeadError!!.errorMm, 1e-6)
    }

    @Test
    fun `table swivel angle is computed when workpiece diameter is given`() {
        val result = HelicalIndexing.calculate(
            requiredLeadMm = 180.0,
            leadScrewPitchMm = 6.0,
            characteristicN = 40,
            gearSet = gearSet,
            workpieceDiameterMm = 50.0
        )
        assertNotNull(result.tableSwivelAngleDeg)
        assertTrue(result.tableSwivelAngleDeg!! in 0.0..90.0)
    }

    @Test
    fun `table swivel angle is null when diameter is not provided`() {
        val result = HelicalIndexing.calculate(
            requiredLeadMm = 180.0,
            leadScrewPitchMm = 6.0,
            characteristicN = 40,
            gearSet = gearSet
        )
        assertNull(result.tableSwivelAngleDeg)
    }

    @Test
    fun `empty gear set yields no candidates and no lead error`() {
        val result = HelicalIndexing.calculate(
            requiredLeadMm = 180.0,
            leadScrewPitchMm = 6.0,
            characteristicN = 40,
            gearSet = GearSet("empty", emptyList())
        )
        assertTrue(result.gearChoices.isEmpty())
        assertNull(result.bestLeadError)
    }

    @Test
    fun `far-fetched lead with a minimal gear set is only an approximation`() {
        val result = HelicalIndexing.calculate(
            requiredLeadMm = 7.0,
            leadScrewPitchMm = 6.0,
            characteristicN = 40,
            gearSet = GearSet("tiny", listOf(24, 100))
        )
        assertTrue(result.gearChoices.isNotEmpty())
        assertFalse(result.gearChoices.first().exact)
    }

    @Test
    fun `non positive inputs are rejected`() {
        assertThrows(IllegalArgumentException::class.java) {
            HelicalIndexing.calculate(0.0, 6.0, 40, gearSet)
        }
        assertThrows(IllegalArgumentException::class.java) {
            HelicalIndexing.calculate(180.0, 0.0, 40, gearSet)
        }
        assertThrows(IllegalArgumentException::class.java) {
            HelicalIndexing.calculate(180.0, 6.0, 0, gearSet)
        }
    }
}
