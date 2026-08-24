package com.dividinghead.calculator.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.dividinghead.calculator.data.IdentifiedPreset
import com.dividinghead.calculator.data.PresetRepository
import com.dividinghead.calculator.data.datastore.AppSettings
import com.dividinghead.calculator.data.datastore.SettingsRepository
import com.dividinghead.calculator.data.db.PresetEntity
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

data class PresetUiState(
    val allPresets: List<IdentifiedPreset> = emptyList(),
    val selectedId: String? = null,
    val editingTarget: IdentifiedPreset? = null
) {
    val selected: IdentifiedPreset?
        get() = allPresets.firstOrNull { it.id == selectedId } ?: allPresets.firstOrNull()
}

class PresetViewModel(
    private val presetRepository: PresetRepository,
    private val settingsRepository: SettingsRepository
) : ViewModel() {

    private val editingTarget = MutableStateFlow<IdentifiedPreset?>(null)

    val uiState: StateFlow<PresetUiState> = combine(
        presetRepository.allPresets,
        settingsRepository.settings,
        editingTarget
    ) { presets, settings, editing ->
        PresetUiState(allPresets = presets, selectedId = settings.selectedPresetId, editingTarget = editing)
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), PresetUiState())

    fun selectPreset(id: String) {
        viewModelScope.launch { settingsRepository.setSelectedPreset(id) }
    }

    /** Opens the edit form pre-filled from [preset]. Works for both custom presets (edited
     * in place) and built-in ones (edited as a new custom copy, since built-ins are read-only). */
    fun startEditing(preset: IdentifiedPreset) {
        editingTarget.value = preset
    }

    /** Opens the edit form blank, for creating a brand new preset from scratch. */
    fun startCreating() {
        editingTarget.value = null
    }

    fun cancelEditing() {
        editingTarget.value = null
    }

    /**
     * Saves the preset currently being edited (updating it in place if it's an existing custom
     * preset, or creating a new custom one otherwise — including when cloning a built-in preset)
     * and immediately selects it, so the change takes effect right away.
     */
    fun saveCustomPreset(
        name: String,
        characteristicN: Int,
        circles: List<Int>,
        gears: List<Int>,
        leadScrewPitchMm: Double,
        isMetric: Boolean
    ) {
        val editingCustomEntity = editingTarget.value?.takeIf { !it.isBuiltIn }?.entity
        viewModelScope.launch {
            val newId: Long
            if (editingCustomEntity != null) {
                val updated = editingCustomEntity.copy(
                    name = name,
                    characteristicN = characteristicN,
                    circlesCsv = circles.joinToString(","),
                    gearsCsv = gears.joinToString(","),
                    leadScrewPitchMm = leadScrewPitchMm,
                    isMetric = isMetric
                )
                presetRepository.updateCustomPreset(updated)
                newId = updated.id
            } else {
                newId = presetRepository.saveCustomPreset(
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
            settingsRepository.setSelectedPreset(AppSettings.CUSTOM_PRESET_PREFIX + newId)
            editingTarget.value = null
        }
    }

    fun deleteCustomPreset(preset: IdentifiedPreset) {
        val entity = preset.entity ?: return
        viewModelScope.launch { presetRepository.deleteCustomPreset(entity) }
    }
}
