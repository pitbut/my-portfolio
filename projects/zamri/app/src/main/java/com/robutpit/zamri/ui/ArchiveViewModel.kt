package com.robutpit.zamri.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.robutpit.zamri.ZamriApp
import com.robutpit.zamri.data.GameRepository
import com.robutpit.zamri.data.db.ViolationEntity
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

/** Backs the "Архив нарушений" gallery: all captured snapshots, filterable by round. */
class ArchiveViewModel(private val repository: GameRepository) : ViewModel() {

    private val _selectedRound = MutableStateFlow<Int?>(null)
    val selectedRound: StateFlow<Int?> = _selectedRound.asStateFlow()

    private val allViolations = repository.observeAll()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val availableRounds: StateFlow<List<Int>> = allViolations
        .map { list -> list.map { it.round }.distinct().sortedDescending() }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val filteredViolations: StateFlow<List<ViolationEntity>> = combine(
        allViolations, _selectedRound
    ) { all, round ->
        if (round == null) all else all.filter { it.round == round }
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    fun selectRound(round: Int?) {
        _selectedRound.value = round
    }

    fun clearArchive() {
        viewModelScope.launch { repository.clearArchive() }
    }
}

class ArchiveViewModelFactory(private val app: ZamriApp) : ViewModelProvider.Factory {
    @Suppress("UNCHECKED_CAST")
    override fun <T : ViewModel> create(modelClass: Class<T>): T {
        require(modelClass.isAssignableFrom(ArchiveViewModel::class.java))
        return ArchiveViewModel(app.repository) as T
    }
}
