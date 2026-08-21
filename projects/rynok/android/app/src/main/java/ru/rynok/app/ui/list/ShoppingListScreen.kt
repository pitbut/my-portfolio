package ru.rynok.app.ui.list

import android.Manifest
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.weight
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.Send
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import kotlinx.coroutines.launch
import ru.rynok.app.data.local.ListStatus
import ru.rynok.app.domain.formatMoney
import ru.rynok.app.voice.SpeechInputManager
import ru.rynok.app.voice.VoiceItemParser

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ShoppingListScreen() {
    val viewModel: ShoppingListViewModel = viewModel()
    val state by viewModel.uiState.collectAsState()
    val context = LocalContext.current
    val scope = rememberCoroutineScope()

    var name by remember { mutableStateOf("") }
    var quantity by remember { mutableStateOf("") }
    var price by remember { mutableStateOf("") }
    var recognitionError by remember { mutableStateOf<String?>(null) }

    val speechManager = remember { SpeechInputManager(context) }
    val micPermissionLauncher = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        if (granted) {
            speechManager.startListening(
                onResult = { text ->
                    scope.launch { viewModel.addParsedItem(VoiceItemParser.parse(text)) }
                },
                onError = { recognitionError = it },
            )
        } else {
            recognitionError = "Нужен доступ к микрофону"
        }
    }

    Scaffold(
        topBar = { TopAppBar(title = { Text("Список покупок") }) },
    ) { padding ->
        Column(modifier = Modifier.fillMaxSize().padding(padding).padding(16.dp)) {

            if (state.status != ListStatus.DRAFT) {
                Card(modifier = Modifier.fillMaxWidth().padding(bottom = 12.dp)) {
                    Text(
                        text = when (state.status) {
                            ListStatus.SENT -> "Список отправлен, ждём начала покупок"
                            ListStatus.SHOPPING -> "Муж уже в магазине — список меняется в реальном времени"
                            else -> ""
                        },
                        modifier = Modifier.padding(12.dp),
                    )
                }
            }

            if (state.status == ListStatus.DRAFT) {
                Row(verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
                    OutlinedTextField(
                        value = name,
                        onValueChange = { name = it },
                        label = { Text("Что купить") },
                        modifier = Modifier.weight(2f),
                    )
                }
                Row(modifier = Modifier.padding(top = 8.dp), verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
                    OutlinedTextField(
                        value = quantity,
                        onValueChange = { quantity = it },
                        label = { Text("Кол-во") },
                        modifier = Modifier.weight(1f),
                    )
                    OutlinedTextField(
                        value = price,
                        onValueChange = { price = it.filter { c -> c.isDigit() || c == '.' } },
                        label = { Text("Цена") },
                        modifier = Modifier.weight(1f).padding(start = 8.dp),
                    )
                    IconButton(onClick = {
                        viewModel.addManualItem(name, quantity, price.toDoubleOrNull())
                        name = ""; quantity = ""; price = ""
                    }) {
                        Icon(Icons.Filled.Add, contentDescription = "Добавить")
                    }
                    IconButton(onClick = {
                        recognitionError = null
                        micPermissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
                    }) {
                        Icon(Icons.Filled.Mic, contentDescription = "Добавить голосом")
                    }
                }
                recognitionError?.let {
                    Text(it, color = androidx.compose.material3.MaterialTheme.colorScheme.error, modifier = Modifier.padding(top = 4.dp))
                }
            }

            LazyColumn(modifier = Modifier.weight(1f).padding(top = 12.dp)) {
                items(state.items, key = { it.id }) { item ->
                    Card(modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth().padding(12.dp),
                            verticalAlignment = androidx.compose.ui.Alignment.CenterVertically,
                        ) {
                            Column(modifier = Modifier.weight(1f)) {
                                Text(item.name, fontWeight = androidx.compose.ui.text.font.FontWeight.Bold)
                                Text(
                                    item.quantity + (item.plannedPrice?.let { " · ${formatMoney(it)}" } ?: ""),
                                    style = androidx.compose.material3.MaterialTheme.typography.bodySmall,
                                )
                                if (item.purchased) {
                                    Text(
                                        "Куплено" + (item.actualPrice?.let { " за ${formatMoney(it)}" } ?: ""),
                                        color = androidx.compose.ui.graphics.Color(0xFF2E7D32),
                                    )
                                }
                            }
                            if (state.status == ListStatus.DRAFT) {
                                IconButton(onClick = { viewModel.removeItem(item) }) {
                                    Icon(Icons.Filled.Delete, contentDescription = "Удалить")
                                }
                            }
                        }
                    }
                }
                if (state.items.isEmpty()) {
                    item { Text("Список пуст. Добавьте товары голосом или вручную", modifier = Modifier.padding(top = 24.dp)) }
                }
            }

            Row(
                modifier = Modifier.fillMaxWidth().padding(top = 8.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = androidx.compose.ui.Alignment.CenterVertically,
            ) {
                Text("Плановый бюджет: ${formatMoney(state.plannedTotal)}", fontWeight = androidx.compose.ui.text.font.FontWeight.Bold)
                if (state.status == ListStatus.DRAFT) {
                    Button(onClick = { viewModel.sendList() }, enabled = state.items.isNotEmpty()) {
                        Icon(Icons.Filled.Send, contentDescription = null)
                        Text(" Отправить", modifier = Modifier.padding(start = 4.dp))
                    }
                }
            }
        }
    }
}
