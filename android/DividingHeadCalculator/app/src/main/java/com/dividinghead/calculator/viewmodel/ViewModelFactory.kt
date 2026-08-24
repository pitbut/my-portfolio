package com.dividinghead.calculator.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import com.dividinghead.calculator.DividingHeadApplication

class AppViewModelFactory(private val app: DividingHeadApplication) : ViewModelProvider.Factory {
    @Suppress("UNCHECKED_CAST")
    override fun <T : ViewModel> create(modelClass: Class<T>): T {
        return when {
            modelClass.isAssignableFrom(SettingsViewModel::class.java) ->
                SettingsViewModel(app.settingsRepository) as T

            modelClass.isAssignableFrom(PresetViewModel::class.java) ->
                PresetViewModel(app.presetRepository, app.settingsRepository) as T

            modelClass.isAssignableFrom(SimpleIndexingViewModel::class.java) ->
                SimpleIndexingViewModel(app.presetRepository, app.settingsRepository, app.historyRepository) as T

            modelClass.isAssignableFrom(DifferentialIndexingViewModel::class.java) ->
                DifferentialIndexingViewModel(app.presetRepository, app.settingsRepository, app.historyRepository) as T

            modelClass.isAssignableFrom(HelicalIndexingViewModel::class.java) ->
                HelicalIndexingViewModel(app.presetRepository, app.settingsRepository, app.historyRepository) as T

            modelClass.isAssignableFrom(HistoryViewModel::class.java) ->
                HistoryViewModel(app.historyRepository) as T

            else -> throw IllegalArgumentException("Unknown ViewModel class: ${modelClass.name}")
        }
    }
}
