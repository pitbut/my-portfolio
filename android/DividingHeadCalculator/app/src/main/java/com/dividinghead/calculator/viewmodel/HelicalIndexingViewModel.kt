package com.dividinghead.calculator.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.dividinghead.calc.GearCombination
import com.dividinghead.calc.HelicalIndexing
import com.dividinghead.calc.HelicalIndexingResult
import com.dividinghead.calc.LeadError
import com.dividinghead.calc.model.DividingHeadPreset
import com.dividinghead.calculator.data.HistoryRepository
import com.dividinghead.calculator.data.PresetRepository
import com.dividinghead.calculator.data.datastore.SettingsRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

data class HelicalScreenState(
    val presetName: String = "",
    val preset: DividingHeadPreset? = null,
    val leadText: String = "",
    val pitchText: String = "6.0",
    val diameterText: String = "",
    val useInches: Boolean = false,
    val result: HelicalIndexingResult? = null,
    val selectedGearIndex: Int = 0,
    val errorMessage: String? = null
) {
    val selectedGear: GearCombination? get() = result?.gearChoices?.getOrNull(selectedGearIndex)
    val selectedLeadError: LeadError?
        get() {
            val r = result ?: return null
            val g = selectedGear ?: return null
            return HelicalIndexing.leadErrorFor(g, r.characteristicN, r.leadScrewPitchMm, r.requiredLeadMm)
        }
}

class HelicalIndexingViewModel(
    presetRepository: PresetRepository,
    settingsRepository: SettingsRepository,
    private val historyRepository: HistoryRepository
) : ViewModel() {

    private val currentPreset = combine(presetRepository.allPresets, settingsRepository.settings) { presets, settings ->
        presets.firstOrNull { it.id == settings.selectedPresetId }?.preset ?: presets.firstOrNull()?.preset
    }

    private val leadText = MutableStateFlow("")
    private val pitchText = MutableStateFlow("6.0")
    private val diameterText = MutableStateFlow("")
    private val useInches = MutableStateFlow(false)
    private val result = MutableStateFlow<HelicalIndexingResult?>(null)
    private val selectedGearIndex = MutableStateFlow(0)
    private val error = MutableStateFlow<String?>(null)

    val uiState: StateFlow<HelicalScreenState> = combine(
        currentPreset, leadText, pitchText, diameterText, useInches
    ) { preset, lead, pitch, diameter, inches ->
        HelicalScreenState(
            presetName = preset?.name ?: "",
            preset = preset,
            leadText = lead,
            pitchText = pitch,
            diameterText = diameter,
            useInches = inches
        )
    }.combine(result) { s, r -> s.copy(result = r) }
        .combine(selectedGearIndex) { s, i -> s.copy(selectedGearIndex = i) }
        .combine(error) { s, e -> s.copy(errorMessage = e) }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), HelicalScreenState())

    fun initPitchFromPreset(pitch: Double) {
        if (pitchText.value.isBlank() || pitchText.value == "6.0") pitchText.value = pitch.toString()
    }

    fun onLeadChanged(text: String) { leadText.value = text; result.value = null; error.value = null }
    fun onPitchChanged(text: String) { pitchText.value = text; result.value = null; error.value = null }
    fun onDiameterChanged(text: String) { diameterText.value = text; result.value = null; error.value = null }
    fun onUnitToggle(inches: Boolean) { useInches.value = inches; result.value = null; error.value = null }

    fun selectGear(index: Int) {
        if (index in (result.value?.gearChoices?.indices ?: IntRange.EMPTY)) selectedGearIndex.value = index
    }

    fun calculate() {
        val preset = uiState.value.preset ?: return
        val lead = leadText.value.toDoubleOrNull()
        val pitch = pitchText.value.toDoubleOrNull()
        val diameter = diameterText.value.toDoubleOrNull()

        if (lead == null || lead <= 0.0) {
            error.value = "Введите шаг спирали больше нуля"
            return
        }
        if (pitch == null || pitch <= 0.0) {
            error.value = "Введите шаг ходового винта больше нуля"
            return
        }

        runCatching {
            HelicalIndexing.calculate(
                requiredLeadMm = lead,
                leadScrewPitchMm = pitch,
                characteristicN = preset.characteristicN,
                gearSet = preset.gearSet,
                workpieceDiameterMm = diameter?.takeIf { it > 0.0 }
            )
        }.onSuccess { r ->
            result.value = r
            selectedGearIndex.value = 0
            error.value = null
            val unit = if (useInches.value) "in" else "мм"
            val best = r.gearChoices.firstOrNull()
            val gearText = best?.let { c ->
                if (c.isCompound) "${c.driver1}/${c.driven1} и ${c.driver2}/${c.driven2}" else "${c.driver1}/${c.driven1}"
            } ?: "—"
            viewModelScope.launch {
                historyRepository.record(
                    mode = "Винтовое деление",
                    summary = "T=$lead $unit, Pв=$pitch, N=${preset.characteristicN}",
                    details = "Шестерни: $gearText"
                )
            }
        }.onFailure {
            result.value = null
            error.value = it.message ?: "Ошибка расчёта"
        }
    }
}
