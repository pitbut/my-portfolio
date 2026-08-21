package ru.rynok.app.ui.family

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import ru.rynok.app.FamilyRole
import ru.rynok.app.RynokApp
import ru.rynok.app.data.remote.RelayApi

sealed class FamilySetupState {
    data object Choosing : FamilySetupState()
    data object Loading : FamilySetupState()
    data class CodeReady(val code: String) : FamilySetupState()
    data class Error(val message: String) : FamilySetupState()
    data object Done : FamilySetupState()
}

class FamilyViewModel(application: Application) : AndroidViewModel(application) {

    private val app get() = getApplication<RynokApp>()
    private val relayApi = RelayApi()

    private val _state = MutableStateFlow<FamilySetupState>(FamilySetupState.Choosing)
    val state: StateFlow<FamilySetupState> = _state

    fun createFamily() {
        _state.value = FamilySetupState.Loading
        viewModelScope.launch {
            relayApi.createFamily()
                .onSuccess { created ->
                    app.prefs.familyId = created.familyId
                    app.prefs.role = FamilyRole.WIFE
                    app.prefs.familyCode = created.code
                    _state.value = FamilySetupState.CodeReady(created.code)
                }
                .onFailure {
                    _state.value = FamilySetupState.Error("Не удалось создать список. Проверьте подключение к интернету")
                }
        }
    }

    fun confirmCodeShared() {
        app.relayClient.connect()
        _state.value = FamilySetupState.Done
    }

    fun joinFamily(code: String) {
        if (code.length < 4) {
            _state.value = FamilySetupState.Error("Введите код полностью")
            return
        }
        _state.value = FamilySetupState.Loading
        viewModelScope.launch {
            relayApi.joinFamily(code)
                .onSuccess { familyId ->
                    app.prefs.familyId = familyId
                    app.prefs.role = FamilyRole.HUSBAND
                    app.prefs.familyCode = code
                    app.relayClient.connect()
                    _state.value = FamilySetupState.Done
                }
                .onFailure {
                    _state.value = FamilySetupState.Error("Код не найден. Проверьте цифры и попробуйте снова")
                }
        }
    }

    fun resetToChoosing() {
        _state.value = FamilySetupState.Choosing
    }
}
