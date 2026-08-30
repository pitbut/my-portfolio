package com.robutpit.zamri.data

import android.content.Context
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

private val Context.dataStore by preferencesDataStore(name = "zamri_settings")

class SettingsStore(private val context: Context) {

    val settings: Flow<GameSettings> = context.dataStore.data.map { prefs ->
        GameSettings(
            roundDurationSec = prefs[ROUND_DURATION] ?: GameSettings().roundDurationSec,
            greenMinSec = prefs[GREEN_MIN] ?: GameSettings().greenMinSec,
            greenMaxSec = prefs[GREEN_MAX] ?: GameSettings().greenMaxSec,
            redFreezeSec = prefs[RED_FREEZE] ?: GameSettings().redFreezeSec,
            sectorCount = prefs[SECTORS] ?: GameSettings().sectorCount,
            soundEnabled = prefs[SOUND_ENABLED] ?: GameSettings().soundEnabled,
            volumePercent = prefs[VOLUME] ?: GameSettings().volumePercent,
            sensitivityPercent = prefs[SENSITIVITY] ?: GameSettings().sensitivityPercent
        )
    }

    suspend fun update(settings: GameSettings) {
        context.dataStore.edit { prefs ->
            prefs[ROUND_DURATION] = settings.roundDurationSec
            prefs[GREEN_MIN] = settings.greenMinSec
            prefs[GREEN_MAX] = settings.greenMaxSec
            prefs[RED_FREEZE] = settings.redFreezeSec
            prefs[SECTORS] = settings.sectorCount
            prefs[SOUND_ENABLED] = settings.soundEnabled
            prefs[VOLUME] = settings.volumePercent
            prefs[SENSITIVITY] = settings.sensitivityPercent
        }
    }

    companion object {
        private val ROUND_DURATION = intPreferencesKey("round_duration_sec")
        private val GREEN_MIN = intPreferencesKey("green_min_sec")
        private val GREEN_MAX = intPreferencesKey("green_max_sec")
        private val RED_FREEZE = intPreferencesKey("red_freeze_sec")
        private val SECTORS = intPreferencesKey("sector_count")
        private val SOUND_ENABLED = booleanPreferencesKey("sound_enabled")
        private val VOLUME = intPreferencesKey("volume_percent")
        private val SENSITIVITY = intPreferencesKey("sensitivity_percent")
    }
}
