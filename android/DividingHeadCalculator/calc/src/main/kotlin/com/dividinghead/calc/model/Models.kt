package com.dividinghead.calc.model

/** One physical index plate (disc) carrying several circles of holes. */
data class IndexPlate(
    val name: String,
    val circles: List<Int>
)

/** A full set of index plates supplied with a dividing head (e.g. Brown & Sharpe). */
data class IndexPlateSet(
    val name: String,
    val plates: List<IndexPlate>
) {
    val allCircles: List<Int> get() = plates.flatMap { it.circles }.distinct().sorted()

    /** The plate a given circle belongs to, or null if it is not part of this set. */
    fun plateFor(circle: Int): IndexPlate? = plates.firstOrNull { circle in it.circles }
}

/** A set of standard change gears available for the differential/helical "gitara". */
data class GearSet(
    val name: String,
    val gears: List<Int>
)

/** A complete preset describing one physical dividing head configuration. */
data class DividingHeadPreset(
    val name: String,
    val characteristicN: Int,
    val plateSet: IndexPlateSet,
    val gearSet: GearSet,
    val leadScrewPitchMm: Double = 6.0,
    val isMetric: Boolean = true
)
