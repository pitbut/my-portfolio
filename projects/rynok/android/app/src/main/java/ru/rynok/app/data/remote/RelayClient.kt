package ru.rynok.app.data.remote

import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import ru.rynok.app.BuildConfig
import ru.rynok.app.Prefs
import java.util.concurrent.TimeUnit

/**
 * Держит одно WebSocket-соединение с сервером-релеем. Подключается, когда
 * приложение на переднем плане, переподключается с нарастающей паузой при
 * обрыве. Сервер сам буферизует события для офлайн-получателя, поэтому
 * пропуски связи не теряют данные — они просто придут при следующем connect().
 */
class RelayClient(private val prefs: Prefs) {

    private val httpClient = OkHttpClient.Builder()
        .readTimeout(0, TimeUnit.MILLISECONDS) // WebSocket живёт долго — не рвём по read timeout
        .build()

    private var webSocket: WebSocket? = null
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private var reconnectJob: Job? = null
    private var reconnectAttempt = 0

    private val _events = MutableSharedFlow<SyncEvent>(extraBufferCapacity = 64)
    val events: SharedFlow<SyncEvent> = _events

    private val _isConnected = MutableStateFlow(false)
    val isConnected: StateFlow<Boolean> = _isConnected

    fun connect() {
        val familyId = prefs.familyId ?: return
        val role = prefs.role ?: return

        reconnectJob?.cancel()
        webSocket?.close(1000, null)

        val url = "${BuildConfig.RELAY_WS_URL}?familyId=$familyId&role=${role.wireValue}"
        val request = Request.Builder().url(url).build()
        webSocket = httpClient.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                reconnectAttempt = 0
                _isConnected.value = true
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                scope.launch { _events.emit(parseSyncEvent(text)) }
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                _isConnected.value = false
                scheduleReconnect()
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                _isConnected.value = false
                scheduleReconnect()
            }
        })
    }

    fun send(event: SyncEvent) {
        webSocket?.send(event.toJson())
    }

    fun disconnect() {
        reconnectJob?.cancel()
        webSocket?.close(1000, null)
        webSocket = null
        _isConnected.value = false
    }

    private fun scheduleReconnect() {
        if (prefs.familyId == null) return
        reconnectJob?.cancel()
        reconnectAttempt = (reconnectAttempt + 1).coerceAtMost(6)
        val delayMs = (1000L * (1 shl reconnectAttempt)).coerceAtMost(30_000L)
        reconnectJob = scope.launch {
            delay(delayMs)
            connect()
        }
    }
}
