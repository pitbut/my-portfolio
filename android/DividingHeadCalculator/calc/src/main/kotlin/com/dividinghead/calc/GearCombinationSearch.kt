package com.dividinghead.calc

import kotlin.math.abs

/**
 * One candidate change-gear ("gitara") train.
 *
 * Single pair: driver1 -> driven1, ratio = driver1 / driven1.
 * Compound (two pairs on an intermediate stud): driver1 -> driven1 (mounted on stud)
 * driver2 -> driven2, ratio = (driver1 * driver2) / (driven1 * driven2).
 */
data class GearCombination(
    val driver1: Int,
    val driven1: Int,
    val driver2: Int? = null,
    val driven2: Int? = null,
    val achievedRatio: Double,
    val errorPercent: Double,
    val exact: Boolean,
    val feasible: Boolean
) {
    val isCompound: Boolean get() = driver2 != null && driven2 != null
    val meshCount: Int get() = if (isCompound) 2 else 1
}

object GearCombinationSearch {

    /**
     * Brute-forces all single-pair and compound (two-pair) gear combinations from [gears]
     * and returns up to [maxResults] candidates sorted by ascending error, closest first.
     */
    fun findBestCombinations(
        target: Fraction,
        gears: List<Int>,
        maxResults: Int = 5,
        includeCompound: Boolean = true
    ): List<GearCombination> {
        if (gears.isEmpty()) return emptyList()
        val targetReduced = target.reduced()
        val targetDouble = target.toDouble()
        if (targetDouble <= 0.0) return emptyList()

        val results = mutableListOf<GearCombination>()

        for (a in gears) {
            for (b in gears) {
                val achieved = Fraction.of(a, b)
                val exact = achieved.reduced() == targetReduced
                val errorPercent = (achieved.toDouble() - targetDouble) / targetDouble * 100.0
                results += GearCombination(
                    driver1 = a,
                    driven1 = b,
                    achievedRatio = achieved.toDouble(),
                    errorPercent = errorPercent,
                    exact = exact,
                    feasible = true
                )
            }
        }

        if (includeCompound) {
            for (a in gears) {
                for (b in gears) {
                    for (c in gears) {
                        for (d in gears) {
                            val achieved = Fraction.of(a.toLong() * c, b.toLong() * d)
                            val exact = achieved.reduced() == targetReduced
                            val errorPercent = (achieved.toDouble() - targetDouble) / targetDouble * 100.0
                            // Clearance rule of thumb for the two stud-mounted gears (b and c)
                            // so they clear the outer driver/driven gears (a and d).
                            val feasible = (b + c) > (a + d) / 2.0 + 4
                            results += GearCombination(
                                driver1 = a,
                                driven1 = b,
                                driver2 = c,
                                driven2 = d,
                                achievedRatio = achieved.toDouble(),
                                errorPercent = errorPercent,
                                exact = exact,
                                feasible = feasible
                            )
                        }
                    }
                }
            }
        }

        return results
            .sortedWith(
                compareBy(
                    { !it.feasible },
                    { abs(it.errorPercent) },
                    { it.meshCount }
                )
            )
            .distinct()
            .take(maxResults)
    }
}
