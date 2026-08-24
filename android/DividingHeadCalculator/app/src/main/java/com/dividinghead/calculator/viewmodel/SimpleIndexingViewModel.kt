package com.dividinghead.calculator.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.dividinghead.calc.SimpleIndexing
import com.dividinghead.calc.SimpleIndexingResult
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
import kotlin.math.roundToInt

data class SimpleScreenState(
    val presetName: String = "",
    val preset: DividingHeadPreset? = null,
    val nText: String = "",
    val alternatives: List<SimpleIndexingResult> = emptyList(),
    val selectedIndex: Int = 0,
    val errorMessage: String? = null
) {
    val result: SimpleIndexingResult? get() = alternatives.getOrNull(selectedIndex)
}

class SimpleIndexingViewModel(
    presetRepository: PresetRepository,
    settingsRepository: SettingsRepository,
    private val historyRepository: HistoryRepository
) : ViewModel() {

    private val currentPreset = combine(presetRepository.allPresets, settingsRepository.settings) { presets, settings ->
        presets.firstOrNull { it.id == settings.selectedPresetId }?.preset ?: presets.firstOrNull()?.preset
    }

    private val nText = MutableStateFlow("")
    private val alternatives = MutableStateFlow<List<SimpleIndexingResult>>(emptyList())
    private val selectedIndex = MutableStateFlow(0)
    private val error = MutableStateFlow<String?>(null)

    val uiState: StateFlow<SimpleScreenState> = combine(
        currentPreset, nText, alternatives, selectedIndex, error
    ) { preset, n, alts, index, err ->
        SimpleScreenState(
            presetName = preset?.name ?: "",
            preset = preset,
            nText = n,
            alternatives = alts,
            selectedIndex = index,
            errorMessage = err
        )
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), SimpleScreenState())

    fun onNChanged(text: String) {
        nText.value = text.filter { it.isDigit() }
        alternatives.value = emptyList()
        selectedIndex.value = 0
        error.value = null
    }

    fun calculate() {
        val preset = uiState.value.preset ?: return
        val n = nText.value.toIntOrNull()
        if (n == null || n <= 0) {
            error.value = "Введите положительное число делений"
            return
        }
        runCatching { SimpleIndexing.calculateAlternatives(n, preset.characteristicN, preset.plateSet, maxResults = 6) }
            .onSuccess { results ->
                alternatives.value = results
                selectedIndex.value = 0
                error.value = null
                recordHistory(preset.name, n, preset.characteristicN, results.first())
            }
            .onFailure {
                alternatives.value = emptyList()
                error.value = it.message ?: "Ошибка расчёта"
            }
    }

    fun selectAlternative(index: Int) {
        if (index in alternatives.value.indices) selectedIndex.value = index
    }

    private fun recordHistory(presetName: String, n: Int, characteristicN: Int, r: SimpleIndexingResult) {
        viewModelScope.launch {
            historyRepository.record(
                mode = "Простое деление",
                summary = "n=$n, N=$characteristicN",
                details = if (r.hasFraction)
                    "${r.wholeTurns} об. + ${r.holes} отв. на круге ${r.circleHoles} ($presetName)"
                else
                    "${r.wholeTurns} полных оборотов"
            )
        }
    }
}

/** Rounds an angular error in degrees to whole arcseconds for display. */
fun Double.toArcSecondsRounded(): Int = (this).roundToInt()
