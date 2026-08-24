package com.dividinghead.calc

import com.dividinghead.calc.model.GearSet
import kotlin.math.PI
import kotlin.math.atan
import kotlin.math.roundToLong

/** Error of the resulting spiral lead if the chosen gear combination is only approximate. */
data class LeadError(val achievedLeadMm: Double, val errorMm: Double, val errorPercent: Double)

data class HelicalIndexingResult(
    val requiredLeadMm: Double,
    val leadScrewPitchMm: Double,
    val characteristicN: Int,
    val gearRatioTarget: Fraction,
    val gearChoices: List<GearCombination>,
    val tableSwivelAngleDeg: Double?,
    val bestLeadError: LeadError?
)

object HelicalIndexing {

    private const val PRECISION = 1_000_000L

    /**
     * @param requiredLeadMm required lead of the spiral/helix (T), in mm
     * @param leadScrewPitchMm pitch of the table lead screw (Pv), default 6 mm, editable
     * @param characteristicN dividing head characteristic (N), default 40, editable
     * @param workpieceDiameterMm optional workpiece diameter, used to compute the table swivel angle
     */
    fun calculate(
        requiredLeadMm: Double,
        leadScrewPitchMm: Double,
        characteristicN: Int,
        gearSet: GearSet,
        workpieceDiameterMm: Double? = null,
        maxGearResults: Int = 5
    ): HelicalIndexingResult {
        require(requiredLeadMm > 0) { "Шаг спирали должен быть положительным" }
        require(leadScrewPitchMm > 0) { "Шаг ходового винта должен быть положительным" }
        require(characteristicN > 0) { "Характеристика головки должна быть положительной" }

        // i = (N * Pv) / T, kept as an exact-enough rational via fixed-point scaling.
        val pvScaled = (leadScrewPitchMm * PRECISION).roundToLong()
        val tScaled = (requiredLeadMm * PRECISION).roundToLong()
        val target = Fraction.of(characteristicN.toLong() * pvScaled, tScaled).reduced()

        val choices = GearCombinationSearch.findBestCombinations(target, gearSet.gears, maxGearResults)

        val angle = workpieceDiameterMm?.let { d ->
            Math.toDegrees(atan(PI * d / requiredLeadMm))
        }

        val bestError = choices.firstOrNull { it.feasible }?.let { best ->
            leadErrorFor(best, characteristicN, leadScrewPitchMm, requiredLeadMm)
        }

        return HelicalIndexingResult(
            requiredLeadMm = requiredLeadMm,
            leadScrewPitchMm = leadScrewPitchMm,
            characteristicN = characteristicN,
            gearRatioTarget = target,
            gearChoices = choices,
            tableSwivelAngleDeg = angle,
            bestLeadError = bestError
        )
    }

    /** Computes the resulting lead and its error for a specific (e.g. user-selected) gear combination. */
    fun leadErrorFor(
        combination: GearCombination,
        characteristicN: Int,
        leadScrewPitchMm: Double,
        requiredLeadMm: Double
    ): LeadError {
        val achievedLead = characteristicN * leadScrewPitchMm / combination.achievedRatio
        val errorMm = achievedLead - requiredLeadMm
        return LeadError(achievedLead, errorMm, errorMm / requiredLeadMm * 100.0)
    }
}
