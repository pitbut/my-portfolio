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
    val result: SimpleIndexingResult? = null,
    val errorMessage: String? = null
)

class SimpleIndexingViewModel(
    presetRepository: PresetRepository,
    settingsRepository: SettingsRepository,
    private val historyRepository: HistoryRepository
) : ViewModel() {

    private val currentPreset = combine(presetRepository.allPresets, settingsRepository.settings) { presets, settings ->
        presets.firstOrNull { it.id == settings.selectedPresetId }?.preset ?: presets.firstOrNull()?.preset
    }

    private val nText = MutableStateFlow("")
    private val result = MutableStateFlow<SimpleIndexingResult?>(null)
    private val error = MutableStateFlow<String?>(null)

    val uiState: StateFlow<SimpleScreenState> = combine(currentPreset, nText, result, error) { preset, n, res, err ->
        SimpleScreenState(
            presetName = preset?.name ?: "",
            preset = preset,
            nText = n,
            result = res,
            errorMessage = err
        )
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), SimpleScreenState())

    fun onNChanged(text: String) {
        nText.value = text.filter { it.isDigit() }
        result.value = null
        error.value = null
    }

    fun calculate() {
        val preset = uiState.value.preset ?: return
        val n = nText.value.toIntOrNull()
        if (n == null || n <= 0) {
            error.value = "Введите положительное число делений"
            return
        }
        runCatching { SimpleIndexing.calculate(n, preset.characteristicN, preset.plateSet) }
            .onSuccess { r ->
                result.value = r
                error.value = null
                viewModelScope.launch {
                    historyRepository.record(
                        mode = "Простое деление",
                        summary = "n=$n, N=${preset.characteristicN}",
                        details = if (r.hasFraction)
                            "${r.wholeTurns} об. + ${r.holes} отв. на круге ${r.circleHoles} (${preset.name})"
                        else
                            "${r.wholeTurns} полных оборотов"
                    )
                }
            }
            .onFailure { error.value = it.message ?: "Ошибка расчёта" }
    }
}

/** Rounds an angular error in degrees to whole arcseconds for display. */
fun Double.toArcSecondsRounded(): Int = (this).roundToInt()
