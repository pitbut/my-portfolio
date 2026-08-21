package ru.rynok.app.ui.shopping

import android.Manifest
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.Checkbox
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import ru.rynok.app.data.local.ShoppingItemEntity
import ru.rynok.app.domain.formatMoney

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ShoppingModeScreen() {
    val viewModel: ShoppingViewModel = viewModel()
    val state by viewModel.uiState.collectAsState()
    var voiceError by remember { mutableStateOf<String?>(null) }

    val micPermissionLauncher = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        if (granted) {
            viewModel.listenForVoiceCommand(onError = { voiceError = it })
        } else {
            voiceError = "Нужен доступ к микрофону"
        }
    }

    Scaffold(
        topBar = { TopAppBar(title = { Text("Покупки") }) },
    ) { padding ->
        Column(modifier = Modifier.fillMaxSize().padding(padding).padding(16.dp)) {

            if (state.listId == null) {
                Text("Пока нет активного списка. Ждём, когда его отправят")
            } else {
                LazyColumn(modifier = Modifier.weight(1f)) {
                    items(state.items, key = { it.id }) { item ->
                        ShoppingItemRow(item = item, onToggle = viewModel::togglePurchased)
                    }
                }

                Card(modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp)) {
                    Column(modifier = Modifier.padding(12.dp)) {
                        Text("План: ${formatMoney(state.plannedTotal)} · Уже потрачено: ${formatMoney(state.actualSoFar)}")
                    }
                }

                voiceError?.let {
                    Text(it, color = MaterialTheme.colorScheme.error, modifier = Modifier.padding(bottom = 4.dp))
                }

                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedButton(onClick = viewModel::announceRemaining, modifier = Modifier.weight(1f)) {
                        Text("Что осталось?")
                    }
                    OutlinedButton(onClick = viewModel::announceBudget, modifier = Modifier.weight(1f)) {
                        Text("Бюджет")
                    }
                    IconButton(onClick = {
                        voiceError = null
                        micPermissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
                    }) {
                        Icon(Icons.Filled.Mic, contentDescription = "Голосовая команда")
                    }
                }

                Button(
                    onClick = viewModel::finishShopping,
                    modifier = Modifier.fillMaxWidth().padding(top = 8.dp),
                    enabled = state.items.isNotEmpty(),
                ) {
                    Text("Завершить покупки")
                }
            }
        }
    }
}

@Composable
private fun ShoppingItemRow(item: ShoppingItemEntity, onToggle: (ShoppingItemEntity, Boolean, Double?) -> Unit) {
    var priceText by remember(item.id) { mutableStateOf(item.actualPrice?.toString() ?: item.plannedPrice?.toString().orEmpty()) }

    Card(modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
        Row(modifier = Modifier.fillMaxWidth().padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
            Checkbox(
                checked = item.purchased,
                onCheckedChange = { checked -> onToggle(item, checked, priceText.toDoubleOrNull()) },
            )
            Column(modifier = Modifier.weight(1f)) {
                Text(item.name, fontWeight = FontWeight.Bold, color = if (item.purchased) Color.Gray else Color.Unspecified)
                Text(item.quantity + (item.plannedPrice?.let { " · план ${formatMoney(it)}" } ?: ""))
            }
            OutlinedTextField(
                value = priceText,
                onValueChange = { new ->
                    priceText = new.filter { c -> c.isDigit() || c == '.' }
                    if (item.purchased) onToggle(item, true, priceText.toDoubleOrNull())
                },
                label = { Text("Цена") },
                modifier = Modifier.weight(0.6f),
            )
        }
    }
}
