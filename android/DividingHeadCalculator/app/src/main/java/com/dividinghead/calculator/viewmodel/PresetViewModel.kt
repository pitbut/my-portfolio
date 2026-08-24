package com.dividinghead.calculator.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.dividinghead.calculator.data.IdentifiedPreset
import com.dividinghead.calculator.data.PresetRepository
import com.dividinghead.calculator.data.datastore.SettingsRepository
import com.dividinghead.calculator.data.db.PresetEntity
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

data class PresetUiState(
    val allPresets: List<IdentifiedPreset> = emptyList(),
    val selectedId: String? = null
) {
    val selected: IdentifiedPreset?
        get() = allPresets.firstOrNull { it.id == selectedId } ?: allPresets.firstOrNull()
}

class PresetViewModel(
    private val presetRepository: PresetRepository,
    private val settingsRepository: SettingsRepository
) : ViewModel() {

    val uiState: StateFlow<PresetUiState> = combine(
        presetRepository.allPresets,
        settingsRepository.settings
    ) { presets, settings ->
        PresetUiState(allPresets = presets, selectedId = settings.selectedPresetId)
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), PresetUiState())

    fun selectPreset(id: String) {
        viewModelScope.launch { settingsRepository.setSelectedPreset(id) }
    }

    fun saveCustomPreset(
        name: String,
        characteristicN: Int,
        circles: List<Int>,
        gears: List<Int>,
        leadScrewPitchMm: Double,
        isMetric: Boolean
    ) {
        viewModelScope.launch {
            presetRepository.saveCustomPreset(
                PresetEntity(
                    name = name,
                    characteristicN = characteristicN,
                    circlesCsv = circles.joinToString(","),
                    gearsCsv = gears.joinToString(","),
                    leadScrewPitchMm = leadScrewPitchMm,
                    isMetric = isMetric
                )
            )
        }
    }

    fun deleteCustomPreset(preset: IdentifiedPreset) {
        val entity = preset.entity ?: return
        viewModelScope.launch { presetRepository.deleteCustomPreset(entity) }
    }
}
