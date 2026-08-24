package com.dividinghead.calculator.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.dividinghead.calculator.data.datastore.AppSettings
import com.dividinghead.calculator.data.datastore.SettingsRepository
import com.dividinghead.calculator.data.datastore.ThemeMode
import com.dividinghead.calculator.data.datastore.UnitSystem
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

class SettingsViewModel(private val repository: SettingsRepository) : ViewModel() {

    val settings: StateFlow<AppSettings> = repository.settings.stateIn(
        scope = viewModelScope,
        started = SharingStarted.WhileSubscribed(5000),
        initialValue = AppSettings()
    )

    fun setThemeMode(mode: ThemeMode) {
        viewModelScope.launch { repository.setThemeMode(mode) }
    }

    fun setLargeFontForShop(enabled: Boolean) {
        viewModelScope.launch { repository.setLargeFontForShop(enabled) }
    }

    fun setUnitSystem(system: UnitSystem) {
        viewModelScope.launch { repository.setUnitSystem(system) }
    }
}
