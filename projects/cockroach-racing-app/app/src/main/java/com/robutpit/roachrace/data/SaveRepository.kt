package com.robutpit.roachrace.data

import android.content.Context
import com.robutpit.roachrace.model.Breed
import com.robutpit.roachrace.model.Levels
import com.robutpit.roachrace.model.ROACH_COLORS
import com.robutpit.roachrace.model.Trait

data class SaveState(
    val breed: Breed?,
    val colorId: String,
    val name: String,
    val traitId: String,
    val levels: Levels,
    /** Satiety at [satietyBaselineAtMillis]; decays over real time since —
     * see RoachEconomy.currentSatiety() for the live value. Not meant to be
     * read directly except by RoachEconomy and the save layer. */
    val satietyBaseline: Int,
    val satietyBaselineAtMillis: Long,
    val lastFedAtMillis: Long,
    val lastTrainedAtMillis: Long,
    val trackId: String?,
    val wins: Int,
    val races: Int,
) {
    /** Custom name if the player set one, otherwise falls back to the breed name. */
    fun displayName(): String = name.ifBlank { breed?.displayName ?: "Таракан" }
    fun trait(): Trait? = Trait.byId(traitId)
}

class SaveRepository(context: Context) {
    private val prefs = context.getSharedPreferences("roach_save_v1", Context.MODE_PRIVATE)

    fun load(): SaveState {
        val breedName = prefs.getString("breed", null)
        val breed = breedName?.let { name -> Breed.entries.firstOrNull { it.name == name } }
        val now = System.currentTimeMillis()
        return SaveState(
            breed = breed,
            colorId = prefs.getString("color", ROACH_COLORS[0].id) ?: ROACH_COLORS[0].id,
            name = prefs.getString("name", "") ?: "",
            traitId = prefs.getString("trait", "") ?: "",
            levels = Levels(
                speed = prefs.getInt("lvl_speed", 0),
                stamina = prefs.getInt("lvl_stamina", 0),
                stress = prefs.getInt("lvl_stress", 0),
            ),
            satietyBaseline = prefs.getInt("satiety_baseline", 70),
            satietyBaselineAtMillis = prefs.getLong("satiety_baseline_at", now),
            lastFedAtMillis = prefs.getLong("last_fed_at", now),
            lastTrainedAtMillis = prefs.getLong("last_trained_at", 0L),
            trackId = prefs.getString("track", null),
            wins = prefs.getInt("wins", 0),
            races = prefs.getInt("races", 0),
        )
    }

    fun save(state: SaveState) {
        prefs.edit().apply {
            putString("breed", state.breed?.name)
            putString("color", state.colorId)
            putString("name", state.name)
            putString("trait", state.traitId)
            putInt("lvl_speed", state.levels.speed)
            putInt("lvl_stamina", state.levels.stamina)
            putInt("lvl_stress", state.levels.stress)
            putInt("satiety_baseline", state.satietyBaseline)
            putLong("satiety_baseline_at", state.satietyBaselineAtMillis)
            putLong("last_fed_at", state.lastFedAtMillis)
            putLong("last_trained_at", state.lastTrainedAtMillis)
            putString("track", state.trackId)
            putInt("wins", state.wins)
            putInt("races", state.races)
        }.apply()
    }

    fun reset() {
        prefs.edit().clear().apply()
    }
}
