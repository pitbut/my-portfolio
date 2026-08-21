package ru.rynok.app.ui.chat

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Send
import androidx.compose.material.icons.filled.Videocam
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.core.content.FileProvider
import androidx.lifecycle.viewmodel.compose.viewModel
import ru.rynok.app.data.local.ChatMessageEntity
import ru.rynok.app.data.local.ChatMessageType
import ru.rynok.app.media.AudioRecorderManager
import ru.rynok.app.media.MediaFiles
import java.io.File
import java.util.concurrent.TimeUnit

@Composable
fun ChatScreen() {
    val viewModel: ChatViewModel = viewModel()
    val messages by viewModel.messages.collectAsState()
    val context = LocalContext.current
    val myRole = viewModel.myRole?.wireValue

    var input by remember { mutableStateOf("") }
    val audioManager = remember { AudioRecorderManager(context) }
    var currentRecordingFile by remember { mutableStateOf<File?>(null) }
    var isRecording by remember { mutableStateOf(false) }

    val videoCaptureFile = remember { mutableStateOf<File?>(null) }
    val videoLauncher = rememberLauncherForActivityResult(ActivityResultContracts.CaptureVideo()) { success ->
        if (success) {
            videoCaptureFile.value?.let { viewModel.sendVideo(it) }
        }
    }
    var hasMicPermission by remember {
        mutableStateOf(
            ContextCompat.checkSelfPermission(context, Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED
        )
    }
    val micPermissionLauncher = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        hasMicPermission = granted
    }

    fun beginRecording() {
        val file = MediaFiles.newVoiceFile(context)
        if (audioManager.startRecording(file)) {
            currentRecordingFile = file
            isRecording = true
        }
    }

    val listState = rememberLazyListState()
    LaunchedEffect(messages.size) {
        if (messages.isNotEmpty()) listState.animateScrollToItem(messages.size - 1)
    }

    Scaffold { padding ->
        Column(modifier = Modifier.fillMaxSize().padding(padding)) {
            LazyColumn(
                state = listState,
                modifier = Modifier.weight(1f).fillMaxWidth().padding(horizontal = 12.dp),
                verticalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                items(messages, key = { it.id }) { message ->
                    ChatBubble(message = message, isMine = message.fromRole == myRole, audioManager = audioManager)
                }
            }

            Row(
                modifier = Modifier.fillMaxWidth().padding(8.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                OutlinedTextField(
                    value = input,
                    onValueChange = { input = it },
                    modifier = Modifier.weight(1f),
                    placeholder = { Text("Сообщение…") },
                )
                IconButton(onClick = { viewModel.sendText(input); input = "" }) {
                    Icon(Icons.Filled.Send, contentDescription = "Отправить")
                }
                IconButton(onClick = {
                    val file = MediaFiles.newVideoFile(context)
                    videoCaptureFile.value = file
                    videoLauncher.launch(MediaFiles.uriFor(context, file))
                }) {
                    Icon(Icons.Filled.Videocam, contentDescription = "Видеосообщение")
                }
                if (!hasMicPermission) {
                    // Разрешение просим обычным тапом — внутри жеста long-press системный
                    // диалог обрывает отслеживание нажатия, поэтому запрашиваем заранее.
                    IconButton(onClick = { micPermissionLauncher.launch(Manifest.permission.RECORD_AUDIO) }) {
                        Icon(Icons.Filled.Mic, contentDescription = "Разрешить микрофон")
                    }
                } else {
                    Box(
                        modifier = Modifier
                            .pointerInput(Unit) {
                                detectTapGestures(
                                    onPress = {
                                        beginRecording()
                                        tryAwaitRelease()
                                        if (isRecording) {
                                            val durationMs = audioManager.stopRecording()
                                            isRecording = false
                                            val file = currentRecordingFile
                                            if (file != null && durationMs != null && durationMs > 300) {
                                                viewModel.sendVoice(file, durationMs)
                                            }
                                            currentRecordingFile = null
                                        }
                                    },
                                )
                            }
                            .background(
                                if (isRecording) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.primary,
                                shape = RoundedCornerShape(50),
                            )
                            .padding(10.dp),
                    ) {
                        Icon(Icons.Filled.Mic, contentDescription = "Удерживайте — голосовое сообщение", tint = androidx.compose.ui.graphics.Color.White)
                    }
                }
            }
        }
    }
}

@Composable
private fun ChatBubble(message: ChatMessageEntity, isMine: Boolean, audioManager: AudioRecorderManager) {
    val context = LocalContext.current
    val bubbleColor = if (isMine) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.surfaceVariant
    val textColor = if (isMine) androidx.compose.ui.graphics.Color.White else MaterialTheme.colorScheme.onSurfaceVariant

    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = if (isMine) Arrangement.End else Arrangement.Start) {
        Box(
            modifier = Modifier
                .widthIn(max = 260.dp)
                .background(bubbleColor, RoundedCornerShape(14.dp))
                .padding(10.dp),
        ) {
            when (message.type) {
                ChatMessageType.TEXT -> Text(message.text.orEmpty(), color = textColor)
                ChatMessageType.VOICE -> Row(verticalAlignment = Alignment.CenterVertically) {
                    IconButton(onClick = {
                        message.localMediaPath?.let { audioManager.play(File(it)) }
                    }) {
                        Icon(Icons.Filled.PlayArrow, contentDescription = "Слушать", tint = textColor)
                    }
                    val seconds = TimeUnit.MILLISECONDS.toSeconds(message.durationMs ?: 0L)
                    Text("Голосовое, ${seconds} сек", color = textColor)
                }
                ChatMessageType.VIDEO -> Row(verticalAlignment = Alignment.CenterVertically) {
                    IconButton(onClick = {
                        val path = message.localMediaPath ?: return@IconButton
                        val uri = FileProvider.getUriForFile(context, "${context.packageName}.fileprovider", File(path))
                        val intent = Intent(Intent.ACTION_VIEW).apply {
                            setDataAndType(uri, "video/mp4")
                            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                        }
                        context.startActivity(intent)
                    }) {
                        Icon(Icons.Filled.PlayArrow, contentDescription = "Смотреть", tint = textColor)
                    }
                    Text("Видеосообщение", color = textColor)
                }
            }
        }
    }
}
