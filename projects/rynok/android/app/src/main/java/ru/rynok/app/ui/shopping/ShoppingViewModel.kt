package ru.rynok.app.ui.shopping

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.filterNotNull
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import ru.rynok.app.RynokApp
import ru.rynok.app.data.local.ListStatus
import ru.rynok.app.data.local.ShoppingItemEntity
import ru.rynok.app.domain.budgetAnnouncement
import ru.rynok.app.voice.SpeechInputManager
import ru.rynok.app.voice.TextToSpeechManager

data class ShoppingUiState(
    val listId: String? = null,
    val status: ListStatus = ListStatus.DRAFT,
    val items: List<ShoppingItemEntity> = emptyList(),
    val plannedTotal: Double = 0.0,
) {
    val remaining get() = items.filter { !it.purchased }
    val actualSoFar get() = items.filter { it.purchased }.sumOf { it.actualPrice ?: 0.0 }
}

class ShoppingViewModel(application: Application) : AndroidViewModel(application) {

    private val repo get() = getApplication<RynokApp>().shoppingRepository
    private val tts by lazy { TextToSpeechManager(getApplication()) }
    private val speech by lazy { SpeechInputManager(getApplication()) }

    val uiState: StateFlow<ShoppingUiState> = repo.observeActiveList()
        .filterNotNull()
        .flatMapLatest { list ->
            repo.observeItems(list.id).map { items ->
                ShoppingUiState(listId = list.id, status = list.status, items = items, plannedTotal = list.plannedTotal)
            }
        }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), ShoppingUiState())

    fun togglePurchased(item: ShoppingItemEntity, purchased: Boolean, actualPrice: Double?) {
        val listId = uiState.value.listId ?: return
        viewModelScope.launch { repo.markPurchased(listId, item, purchased, actualPrice) }
    }

    fun announceRemaining() {
        val remaining = uiState.value.remaining
        val text = if (remaining.isEmpty()) {
            "Всё куплено"
        } else {
            "Осталось купить: " + remaining.joinToString("; ") { "${it.name}, ${it.quantity}" }
        }
        tts.speak(text)
    }

    fun announceBudget() {
        viewModelScope.launch {
            val listId = uiState.value.listId ?: return@launch
            val snapshot = repo.budgetSnapshot(listId, uiState.value.plannedTotal)
            tts.speak(budgetAnnouncement(snapshot))
        }
    }

    /** Голосовая команда: "что осталось" / "бюджет" — озвучиваем ответ. */
    fun listenForVoiceCommand(onError: (String) -> Unit) {
        speech.startListening(
            onResult = { text ->
                val lower = text.lowercase()
                when {
                    lower.contains("осталось") || lower.contains("остал") -> announceRemaining()
                    lower.contains("бюджет") || lower.contains("итог") || lower.contains("сколько") -> announceBudget()
                    else -> tts.speak("Не поняла команду. Спросите «что осталось» или «какой бюджет»")
                }
            },
            onError = onError,
        )
    }

    fun finishShopping() {
        val listId = uiState.value.listId ?: return
        viewModelScope.launch {
            repo.finishShopping(listId, uiState.value.plannedTotal)
            announceBudget()
        }
    }

    override fun onCleared() {
        super.onCleared()
        tts.shutdown()
        speech.stop()
    }
}
