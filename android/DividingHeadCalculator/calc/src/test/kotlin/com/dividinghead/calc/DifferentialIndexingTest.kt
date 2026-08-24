package com.dividinghead.calc

import com.dividinghead.calc.model.Presets
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertThrows
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test

class DifferentialIndexingTest {

    private val plateSet = Presets.brownSharpePlateSet
    private val gearSet = Presets.brownSharpeGearSet

    @Test
    fun `finds 120 as auxiliary number for 127 divisions`() {
        val candidates = DifferentialIndexing.findAuxiliaryCandidates(
            n = 127,
            characteristicN = 40,
            plateSet = plateSet
        )
        assertTrue(120 in candidates)
    }

    @Test
    fun `127 divisions via n'=120 yields an exact gear train and correct direction`() {
        val result = DifferentialIndexing.calculate(
            n = 127,
            nAux = 120,
            characteristicN = 40,
            plateSet = plateSet,
            gearSet = gearSet
        )

        assertTrue(result.plateIndexing.exact)
        // i = N(n' - n)/n' = 40*(120-127)/120 = -7/3
        assertEquals(PlateRotationDirection.OPPOSITE_TO_CRANK, result.direction)
        assertTrue(result.gearChoices.isNotEmpty())
        val best = result.gearChoices.first()
        assertTrue(best.combination.exact)
        assertFalse(best.idlerRequired)
    }

    @Test
    fun `n' greater than n requires plate to turn with the crank`() {
        val result = DifferentialIndexing.calculate(
            n = 100,
            nAux = 120,
            characteristicN = 40,
            plateSet = plateSet,
            gearSet = gearSet
        )
        assertEquals(PlateRotationDirection.SAME_AS_CRANK, result.direction)
    }

    @Test
    fun `nAux equal to n is rejected`() {
        assertThrows(IllegalArgumentException::class.java) {
            DifferentialIndexing.calculate(
                n = 50,
                nAux = 50,
                characteristicN = 40,
                plateSet = plateSet,
                gearSet = gearSet
            )
        }
    }

    @Test
    fun `gear search still returns closest candidates when no exact ratio exists`() {
        val tinyGearSet = com.dividinghead.calc.model.GearSet("tiny", listOf(24, 100))
        val result = DifferentialIndexing.calculate(
            n = 127,
            nAux = 120,
            characteristicN = 40,
            plateSet = plateSet,
            gearSet = tinyGearSet
        )
        assertTrue(result.gearChoices.isNotEmpty())
        assertFalse(result.gearChoices.first().combination.exact)
    }
}
