package ru.rynok.app.ui.chat

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import ru.rynok.app.RynokApp
import ru.rynok.app.data.local.ChatMessageEntity
import ru.rynok.app.data.local.ChatMessageType
import java.io.File

class ChatViewModel(application: Application) : AndroidViewModel(application) {

    private val app get() = getApplication<RynokApp>()
    private val repo get() = app.chatRepository

    val myRole get() = app.prefs.role

    val messages: StateFlow<List<ChatMessageEntity>> =
        (repo.observeMessages() ?: MutableStateFlow(emptyList()))
            .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    fun sendText(text: String) {
        if (text.isBlank()) return
        viewModelScope.launch { repo.sendText(text.trim()) }
    }

    fun sendVoice(file: File, durationMs: Long) {
        viewModelScope.launch { repo.sendMedia(file, ChatMessageType.VOICE, "audio/mp4", durationMs) }
    }

    fun sendVideo(file: File) {
        viewModelScope.launch { repo.sendMedia(file, ChatMessageType.VIDEO, "video/mp4", null) }
    }
}
