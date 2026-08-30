package com.robutpit.roachrace.model

/** One participant's running tally across several Bluetooth heats. Comparing
 * raw finish times across different heats (different opponents, sometimes
 * different tracks) isn't fair, so heats award placement points instead —
 * same idea as a motorsport points table. Immutable + replaced-in-list on
 * update (rather than mutable vars) so Compose's SnapshotStateList notices
 * the change. */
data class TournamentEntry(
    val name: String,
    val points: Int = 0,
    val heats: Int = 0,
    val bestPlace: Int = Int.MAX_VALUE,
)

private val PLACEMENT_POINTS = listOf(10, 8, 6, 5, 4, 3)

fun pointsForPlace(place: Int): Int = PLACEMENT_POINTS.getOrElse(place - 1) { 1 }
