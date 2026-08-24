package com.dividinghead.calc

import com.dividinghead.calc.model.GearSet
import com.dividinghead.calc.model.IndexPlateSet
import kotlin.math.abs

enum class PlateRotationDirection { SAME_AS_CRANK, OPPOSITE_TO_CRANK }

/** A candidate gear train together with whether an idler gear must be added to get [direction] right. */
data class DifferentialGearChoice(
    val combination: GearCombination,
    val idlerRequired: Boolean
)

data class DifferentialIndexingResult(
    val requiredDivisions: Int,
    val auxiliaryDivisions: Int,
    val characteristicN: Int,
    val plateIndexing: SimpleIndexingResult,
    val gearRatio: Fraction,
    val direction: PlateRotationDirection,
    val gearChoices: List<DifferentialGearChoice>
)

object DifferentialIndexing {

    /**
     * Finds auxiliary numbers n' close to [n] for which [plateSet] can index exactly,
     * sorted by closeness to [n]. n' == n is excluded (that would just be simple indexing).
     */
    fun findAuxiliaryCandidates(
        n: Int,
        characteristicN: Int,
        plateSet: IndexPlateSet,
        searchRadius: Int = 40,
        maxResults: Int = 8
    ): List<Int> {
        val candidates = mutableListOf<Int>()
        for (delta in 1..searchRadius) {
            for (nAux in intArrayOf(n - delta, n + delta)) {
                if (nAux <= 0 || nAux == n) continue
                val result = runCatching { SimpleIndexing.calculate(nAux, characteristicN, plateSet) }.getOrNull()
                if (result != null && result.exact) {
                    candidates += nAux
                }
            }
        }
        return candidates.sortedBy { abs(it - n) }.take(maxResults)
    }

    /**
     * Computes the full differential-indexing solution for a chosen auxiliary number [nAux].
     */
    fun calculate(
        n: Int,
        nAux: Int,
        characteristicN: Int,
        plateSet: IndexPlateSet,
        gearSet: GearSet,
        maxGearResults: Int = 5
    ): DifferentialIndexingResult {
        require(n > 0) { "Число делений должно быть положительным" }
        require(nAux > 0 && nAux != n) { "Вспомогательное число должно отличаться от n и быть положительным" }

        val plateIndexing = SimpleIndexing.calculate(nAux, characteristicN, plateSet)

        // i = N * (n' - n) / n'
        val ratio = Fraction.of(
            characteristicN.toLong() * (nAux - n),
            nAux.toLong()
        )
        val magnitude = Fraction(ratio.numerator.abs(), ratio.denominator)

        val direction = if (nAux > n) PlateRotationDirection.SAME_AS_CRANK else PlateRotationDirection.OPPOSITE_TO_CRANK
        val requiredEvenMeshes = direction == PlateRotationDirection.SAME_AS_CRANK

        val combos = GearCombinationSearch.findBestCombinations(magnitude, gearSet.gears, maxGearResults)
        val choices = combos.map { combo ->
            val isEven = combo.meshCount % 2 == 0
            DifferentialGearChoice(combo, idlerRequired = isEven != requiredEvenMeshes)
        }

        return DifferentialIndexingResult(
            requiredDivisions = n,
            auxiliaryDivisions = nAux,
            characteristicN = characteristicN,
            plateIndexing = plateIndexing,
            gearRatio = ratio,
            direction = direction,
            gearChoices = choices
        )
    }
}
