package com.dividinghead.calc

import com.dividinghead.calc.model.IndexPlateSet
import kotlin.math.abs
import kotlin.math.roundToLong

/**
 * Result of a simple (direct) indexing calculation: I = N / n.
 *
 * The handle must be turned [wholeTurns] full turns, plus (if [holes] > 0)
 * [holes] holes on a circle of [circleHoles] holes (circle [plateName]).
 */
data class SimpleIndexingResult(
    val requiredDivisions: Int,
    val characteristicN: Int,
    val wholeTurns: Int,
    val holes: Int,
    val circleHoles: Int,
    val plateName: String?,
    val exact: Boolean,
    val errorArcSeconds: Double,
    val errorPercentOfStep: Double
) {
    val hasFraction: Boolean get() = holes > 0 && circleHoles > 0
}

object SimpleIndexing {

    /**
     * @param n required number of divisions on the workpiece
     * @param characteristicN dividing head characteristic (worm ratio), e.g. 40
     * @param plateSet available index plates to pick a circle from
     */
    fun calculate(n: Int, characteristicN: Int, plateSet: IndexPlateSet): SimpleIndexingResult =
        calculateAlternatives(n, characteristicN, plateSet, maxResults = 1).first()

    /**
     * Same as [calculate], but returns up to [maxResults] candidate circles sorted by
     * ascending error (exact matches first), so the user can choose which one to use
     * instead of always being handed a single auto-picked circle.
     */
    fun calculateAlternatives(
        n: Int,
        characteristicN: Int,
        plateSet: IndexPlateSet,
        maxResults: Int = 5
    ): List<SimpleIndexingResult> {
        require(n > 0) { "Число делений должно быть положительным" }
        require(characteristicN > 0) { "Характеристика головки должна быть положительной" }
        require(maxResults > 0) { "maxResults должен быть положительным" }

        val wholeTurns = characteristicN / n
        val remainder = characteristicN % n

        if (remainder == 0) {
            return listOf(
                SimpleIndexingResult(
                    requiredDivisions = n,
                    characteristicN = characteristicN,
                    wholeTurns = wholeTurns,
                    holes = 0,
                    circleHoles = 0,
                    plateName = null,
                    exact = true,
                    errorArcSeconds = 0.0,
                    errorPercentOfStep = 0.0
                )
            )
        }

        val frac = Fraction.of(remainder, n).reduced()
        val circles = plateSet.allCircles
        require(circles.isNotEmpty()) { "В наборе дисков нет ни одного круга" }

        val stepDeg = 360.0 / n

        val candidates = circles.map { circle ->
            val exact = frac.exactHolesOn(circle)
            val idealHoles = frac.toDouble() * circle
            var holes = idealHoles.roundToLong().toInt()
            if (holes < 1) holes = 1
            if (holes > circle) holes = circle
            val achieved = holes.toDouble() / circle
            val errorDeg = abs(achieved - frac.toDouble()) * (360.0 / characteristicN)
            val errorArcSeconds = errorDeg * 3600.0
            val errorPercentOfStep = if (stepDeg > 0) (errorDeg / stepDeg) * 100.0 else 0.0

            SimpleIndexingResult(
                requiredDivisions = n,
                characteristicN = characteristicN,
                wholeTurns = wholeTurns,
                holes = holes,
                circleHoles = circle,
                plateName = plateSet.plateFor(circle)?.name,
                exact = exact,
                errorArcSeconds = errorArcSeconds,
                errorPercentOfStep = errorPercentOfStep
            )
        }

        return candidates
            .sortedWith(compareBy({ !it.exact }, { it.errorArcSeconds }, { it.circleHoles }))
            .take(maxResults)
    }
}
