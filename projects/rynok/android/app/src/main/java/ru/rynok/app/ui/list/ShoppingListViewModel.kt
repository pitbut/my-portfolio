package ru.rynok.app.ui.list

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.filterNotNull
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.onEach
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import ru.rynok.app.RynokApp
import ru.rynok.app.data.local.ListStatus
import ru.rynok.app.data.local.ShoppingItemEntity
import ru.rynok.app.voice.ParsedItem

data class ListUiState(
    val listId: String? = null,
    val status: ListStatus = ListStatus.DRAFT,
    val items: List<ShoppingItemEntity> = emptyList(),
    val plannedTotal: Double = 0.0,
    val justSent: Boolean = false,
)

class ShoppingListViewModel(application: Application) : AndroidViewModel(application) {

    private val repo get() = getApplication<RynokApp>().shoppingRepository

    init {
        viewModelScope.launch {
            repo.observeActiveList().collect { list ->
                if (list == null) repo.createDraftList()
            }
        }
    }

    val uiState: StateFlow<ListUiState> = repo.observeActiveList()
        .filterNotNull()
        .flatMapLatest { list ->
            repo.observeItems(list.id).map { items ->
                ListUiState(
                    listId = list.id,
                    status = list.status,
                    items = items,
                    plannedTotal = items.sumOf { it.plannedPrice ?: 0.0 },
                )
            }
        }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), ListUiState())

    fun addManualItem(name: String, quantity: String, price: Double?) {
        val listId = uiState.value.listId ?: return
        if (name.isBlank()) return
        viewModelScope.launch {
            repo.addOrUpdateItem(listId, null, name.trim(), quantity.ifBlank { "1 шт" }, price, uiState.value.items.size)
        }
    }

    fun addParsedItem(parsed: ParsedItem) {
        addManualItem(parsed.name, parsed.quantity, parsed.plannedPrice)
    }

    fun removeItem(item: ShoppingItemEntity) {
        viewModelScope.launch { repo.removeItem(item) }
    }

    fun sendList() {
        val listId = uiState.value.listId ?: return
        if (uiState.value.items.isEmpty()) return
        viewModelScope.launch { repo.sendList(listId) }
    }

    fun startNewList() {
        viewModelScope.launch { repo.createDraftList() }
    }
}
