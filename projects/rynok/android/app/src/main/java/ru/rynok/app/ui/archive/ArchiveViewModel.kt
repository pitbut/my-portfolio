package ru.rynok.app.ui.archive

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import ru.rynok.app.RynokApp
import ru.rynok.app.data.local.ShoppingItemEntity
import ru.rynok.app.data.local.ShoppingListEntity

data class ArchiveEntry(val list: ShoppingListEntity, val actualTotal: Double)

class ArchiveViewModel(application: Application) : AndroidViewModel(application) {

    private val repo get() = getApplication<RynokApp>().shoppingRepository

    val archive: StateFlow<List<ArchiveEntry>> = repo.observeArchive()
        .map { lists -> lists.map { list -> ArchiveEntry(list, repo.actualTotalForList(list.id)) } }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    fun itemsFlow(listId: String): Flow<List<ShoppingItemEntity>> = repo.observeItems(listId)
}
