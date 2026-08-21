package ru.rynok.app.data.repository

import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.launch
import ru.rynok.app.Prefs
import ru.rynok.app.data.local.ChatDao
import ru.rynok.app.data.local.ChatMessageEntity
import ru.rynok.app.data.local.ChatMessageType
import ru.rynok.app.data.remote.RelayApi
import ru.rynok.app.data.remote.RelayClient
import ru.rynok.app.data.remote.SyncEvent
import java.io.File
import java.util.UUID

/**
 * Чат хранится ТОЛЬКО локально на каждом телефоне (в Room). Сервер лишь
 * передаёт сообщение другому устройству и ненадолго держит файл голосового
 * /видео сообщения, пока получатель его не скачает. Если пользователь
 * почистит кэш приложения — пропадёт история только у него, это ожидаемо.
 */
class ChatRepository(
    private val chatDao: ChatDao,
    private val relayClient: RelayClient,
    private val prefs: Prefs,
    private val mediaDir: File,
    private val relayApi: RelayApi = RelayApi(),
) {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    init {
        scope.launch {
            relayClient.events.collect { event -> if (event is SyncEvent.ChatMessage) handleIncoming(event) }
        }
    }

    fun observeMessages(): Flow<List<ChatMessageEntity>>? {
        val familyId = prefs.familyId ?: return null
        return chatDao.observeMessages(familyId)
    }

    suspend fun sendText(text: String) {
        val familyId = prefs.familyId ?: return
        val id = UUID.randomUUID().toString()
        val timestamp = System.currentTimeMillis()
        chatDao.insertMessage(
            ChatMessageEntity(
                id = id,
                familyId = familyId,
                fromRole = prefs.role?.wireValue.orEmpty(),
                type = ChatMessageType.TEXT,
                text = text,
                timestamp = timestamp,
            )
        )
        relayClient.send(
            SyncEvent.ChatMessage(id = id, chatType = "TEXT", text = text, mediaId = null, durationMs = null, timestamp = timestamp)
        )
    }

    /** [file] — уже записанный голосовой/видео ролик на этом устройстве. */
    suspend fun sendMedia(file: File, type: ChatMessageType, mimeType: String, durationMs: Long?): Result<Unit> {
        val familyId = prefs.familyId ?: return Result.failure(IllegalStateException("no_family"))
        val uploadResult = relayApi.uploadMedia(file, mimeType)
        val mediaId = uploadResult.getOrElse { return Result.failure(it) }

        val id = UUID.randomUUID().toString()
        val timestamp = System.currentTimeMillis()
        chatDao.insertMessage(
            ChatMessageEntity(
                id = id,
                familyId = familyId,
                fromRole = prefs.role?.wireValue.orEmpty(),
                type = type,
                localMediaPath = file.absolutePath,
                durationMs = durationMs,
                timestamp = timestamp,
            )
        )
        relayClient.send(
            SyncEvent.ChatMessage(
                id = id,
                chatType = type.name,
                text = null,
                mediaId = mediaId,
                durationMs = durationMs,
                timestamp = timestamp,
            )
        )
        return Result.success(Unit)
    }

    private suspend fun handleIncoming(event: SyncEvent.ChatMessage) {
        val familyId = prefs.familyId ?: return
        val type = runCatching { ChatMessageType.valueOf(event.chatType) }.getOrDefault(ChatMessageType.TEXT)

        var localPath: String? = null
        if (type != ChatMessageType.TEXT && event.mediaId != null) {
            val extension = if (type == ChatMessageType.VOICE) "m4a" else "mp4"
            val destination = File(mediaDir, "${event.id}.$extension")
            relayApi.downloadMedia(event.mediaId, destination).onSuccess {
                localPath = destination.absolutePath
            }
        }

        chatDao.insertMessage(
            ChatMessageEntity(
                id = event.id,
                familyId = familyId,
                fromRole = event.fromRole.orEmpty(),
                type = type,
                text = event.text,
                localMediaPath = localPath,
                durationMs = event.durationMs,
                timestamp = event.timestamp,
            )
        )
    }
}
