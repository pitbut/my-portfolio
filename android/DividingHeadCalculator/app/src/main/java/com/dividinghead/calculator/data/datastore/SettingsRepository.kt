package com.dividinghead.calculator.data.datastore

import android.content.Context
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.longPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

private val Context.dataStore by preferencesDataStore(name = "settings")

enum class ThemeMode { SYSTEM, LIGHT, DARK }
enum class UnitSystem { METRIC, IMPERIAL }

data class AppSettings(
    val selectedPresetId: String = BUILTIN_PRESET_PREFIX + "brown_sharpe_40",
    val themeMode: ThemeMode = ThemeMode.SYSTEM,
    val largeFontForShop: Boolean = false,
    val unitSystem: UnitSystem = UnitSystem.METRIC
) {
    companion object {
        const val BUILTIN_PRESET_PREFIX = "builtin:"
        const val CUSTOM_PRESET_PREFIX = "custom:"
    }
}

class SettingsRepository(private val context: Context) {

    private object Keys {
        val SELECTED_PRESET_ID = stringPreferencesKey("selected_preset_id")
        val THEME_MODE = stringPreferencesKey("theme_mode")
        val LARGE_FONT = booleanPreferencesKey("large_font_for_shop")
        val UNIT_SYSTEM = stringPreferencesKey("unit_system")
        val LAST_UPDATED = longPreferencesKey("last_updated")
    }

    val settings: Flow<AppSettings> = context.dataStore.data.map { prefs ->
        AppSettings(
            selectedPresetId = prefs[Keys.SELECTED_PRESET_ID] ?: AppSettings().selectedPresetId,
            themeMode = prefs[Keys.THEME_MODE]?.let { runCatching { ThemeMode.valueOf(it) }.getOrNull() }
                ?: ThemeMode.SYSTEM,
            largeFontForShop = prefs[Keys.LARGE_FONT] ?: false,
            unitSystem = prefs[Keys.UNIT_SYSTEM]?.let { runCatching { UnitSystem.valueOf(it) }.getOrNull() }
                ?: UnitSystem.METRIC
        )
    }

    suspend fun setSelectedPreset(id: String) {
        context.dataStore.edit { it[Keys.SELECTED_PRESET_ID] = id }
    }

    suspend fun setThemeMode(mode: ThemeMode) {
        context.dataStore.edit { it[Keys.THEME_MODE] = mode.name }
    }

    suspend fun setLargeFontForShop(enabled: Boolean) {
        context.dataStore.edit { it[Keys.LARGE_FONT] = enabled }
    }

    suspend fun setUnitSystem(system: UnitSystem) {
        context.dataStore.edit { it[Keys.UNIT_SYSTEM] = system.name }
    }
}
