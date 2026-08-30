package com.robutpit.roachrace.data

import android.content.Context
import com.robutpit.roachrace.model.Breed
import com.robutpit.roachrace.model.Racer

data class BreedStat(val breed: Breed, val wins: Int, val races: Int) {
    val winRatePercent: Int get() = if (races == 0) 0 else (wins * 100 / races)
}

/** Every finished race (solo or Bluetooth, on whichever phone is watching
 * it) records one line into this on-device history: who entered, who won,
 * broken down by breed rather than by individual roach — so over time you
 * can see which species actually races better. Local to this phone, like
 * the rest of the save data. */
class BreedStatsRepository(context: Context) {
    private val prefs = context.getSharedPreferences("breed_stats_v1", Context.MODE_PRIVATE)

    fun recordRaceResult(racers: List<Racer>) {
        if (racers.isEmpty()) return
        val winner = racers.minByOrNull { it.finishOrder ?: Int.MAX_VALUE }
        val edit = prefs.edit()
        val countedBreeds = mutableSetOf<Breed>()
        for (r in racers) {
            // A breed can appear more than once in one race (several bots of
            // the same species, or two players who picked the same breed) —
            // count it as one "race entered" for that breed either way.
            if (countedBreeds.add(r.breed)) {
                edit.putInt(racesKey(r.breed), racesFor(r.breed) + 1)
            }
        }
        winner?.let { edit.putInt(winsKey(it.breed), winsFor(it.breed) + 1) }
        edit.apply()
    }

    fun loadAll(): List<BreedStat> = Breed.entries.map { BreedStat(it, winsFor(it), racesFor(it)) }

    private fun winsFor(breed: Breed) = prefs.getInt(winsKey(breed), 0)
    private fun racesFor(breed: Breed) = prefs.getInt(racesKey(breed), 0)
    private fun winsKey(breed: Breed) = "wins_${breed.name}"
    private fun racesKey(breed: Breed) = "races_${breed.name}"
}
