package com.dividinghead.calculator.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.dividinghead.calculator.data.HistoryRepository
import com.dividinghead.calculator.data.db.HistoryEntity
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

class HistoryViewModel(private val repository: HistoryRepository) : ViewModel() {

    val history: StateFlow<List<HistoryEntity>> = repository.history.stateIn(
        viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList()
    )

    fun delete(entity: HistoryEntity) {
        viewModelScope.launch { repository.delete(entity) }
    }

    fun clear() {
        viewModelScope.launch { repository.clear() }
    }
}
