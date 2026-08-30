package com.robutpit.roachrace.data

import android.content.Context
import com.robutpit.roachrace.model.Breed
import com.robutpit.roachrace.model.Levels
import com.robutpit.roachrace.model.ROACH_COLORS

data class SaveState(
    val breed: Breed?,
    val colorId: String,
    val name: String,
    val levels: Levels,
    val satiety: Int,
    val trackId: String?,
    val wins: Int,
    val races: Int,
) {
    /** Custom name if the player set one, otherwise falls back to the breed name. */
    fun displayName(): String = name.ifBlank { breed?.displayName ?: "Таракан" }
}

class SaveRepository(context: Context) {
    private val prefs = context.getSharedPreferences("roach_save_v1", Context.MODE_PRIVATE)

    fun load(): SaveState {
        val breedName = prefs.getString("breed", null)
        val breed = breedName?.let { name -> Breed.entries.firstOrNull { it.name == name } }
        return SaveState(
            breed = breed,
            colorId = prefs.getString("color", ROACH_COLORS[0].id) ?: ROACH_COLORS[0].id,
            name = prefs.getString("name", "") ?: "",
            levels = Levels(
                speed = prefs.getInt("lvl_speed", 0),
                stamina = prefs.getInt("lvl_stamina", 0),
                stress = prefs.getInt("lvl_stress", 0),
            ),
            satiety = prefs.getInt("satiety", 70),
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
            putInt("lvl_speed", state.levels.speed)
            putInt("lvl_stamina", state.levels.stamina)
            putInt("lvl_stress", state.levels.stress)
            putInt("satiety", state.satiety)
            putString("track", state.trackId)
            putInt("wins", state.wins)
            putInt("races", state.races)
        }.apply()
    }

    fun reset() {
        prefs.edit().clear().apply()
    }
}
