package com.dividinghead.calculator.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.dividinghead.calc.DifferentialIndexing
import com.dividinghead.calc.DifferentialIndexingResult
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

data class DifferentialScreenState(
    val presetName: String = "",
    val preset: DividingHeadPreset? = null,
    val nText: String = "",
    val candidates: List<Int> = emptyList(),
    val selectedAux: Int? = null,
    val result: DifferentialIndexingResult? = null,
    val errorMessage: String? = null
)

class DifferentialIndexingViewModel(
    presetRepository: PresetRepository,
    settingsRepository: SettingsRepository,
    private val historyRepository: HistoryRepository
) : ViewModel() {

    private val currentPreset = combine(presetRepository.allPresets, settingsRepository.settings) { presets, settings ->
        presets.firstOrNull { it.id == settings.selectedPresetId }?.preset ?: presets.firstOrNull()?.preset
    }

    private val nText = MutableStateFlow("")
    private val candidates = MutableStateFlow<List<Int>>(emptyList())
    private val selectedAux = MutableStateFlow<Int?>(null)
    private val result = MutableStateFlow<DifferentialIndexingResult?>(null)
    private val error = MutableStateFlow<String?>(null)

    val uiState: StateFlow<DifferentialScreenState> = combine(
        currentPreset, nText, candidates, selectedAux, result
    ) { preset, n, cands, aux, res ->
        DifferentialScreenState(
            presetName = preset?.name ?: "",
            preset = preset,
            nText = n,
            candidates = cands,
            selectedAux = aux,
            result = res
        )
    }.combine(error) { state, err -> state.copy(errorMessage = err) }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), DifferentialScreenState())

    fun onNChanged(text: String) {
        nText.value = text.filter { it.isDigit() }
        candidates.value = emptyList()
        selectedAux.value = null
        result.value = null
        error.value = null
    }

    fun findAndCalculate() {
        val preset = uiState.value.preset ?: return
        val n = nText.value.toIntOrNull()
        if (n == null || n <= 0) {
            error.value = "Введите положительное число делений"
            return
        }
        val found = DifferentialIndexing.findAuxiliaryCandidates(n, preset.characteristicN, preset.plateSet)
        if (found.isEmpty()) {
            error.value = "Не удалось подобрать вспомогательное число n' в разумном диапазоне"
            candidates.value = emptyList()
            selectedAux.value = null
            result.value = null
            return
        }
        candidates.value = found
        selectAux(found.first())
    }

    fun selectAux(aux: Int) {
        val preset = uiState.value.preset ?: return
        val n = nText.value.toIntOrNull() ?: return
        selectedAux.value = aux
        runCatching {
            DifferentialIndexing.calculate(n, aux, preset.characteristicN, preset.plateSet, preset.gearSet)
        }.onSuccess { r ->
            result.value = r
            error.value = null
            viewModelScope.launch {
                val best = r.gearChoices.firstOrNull()
                val gearText = best?.combination?.let { c ->
                    if (c.isCompound) "${c.driver1}/${c.driven1} и ${c.driver2}/${c.driven2}" else "${c.driver1}/${c.driven1}"
                } ?: "—"
                historyRepository.record(
                    mode = "Дифференциальное деление",
                    summary = "n=$n, n'=$aux, N=${preset.characteristicN}",
                    details = "Шестерни: $gearText"
                )
            }
        }.onFailure {
            error.value = it.message ?: "Ошибка расчёта"
        }
    }
}
