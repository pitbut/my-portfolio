package ru.rynok.app.ui.archive

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Card
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import ru.rynok.app.domain.formatMoney
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ArchiveScreen() {
    val viewModel: ArchiveViewModel = viewModel()
    val archive by viewModel.archive.collectAsState()
    val dateFormat = remember { SimpleDateFormat("d MMMM, HH:mm", Locale("ru")) }
    var expandedListId by remember { mutableStateOf<String?>(null) }

    Scaffold(topBar = { TopAppBar(title = { Text("Архив списков") }) }) { padding ->
        Column(modifier = Modifier.fillMaxSize().padding(padding).padding(16.dp)) {
            if (archive.isEmpty()) {
                Text("Пока нет завершённых списков")
            } else {
                LazyColumn {
                    items(archive, key = { it.list.id }) { entry ->
                        Card(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(vertical = 4.dp)
                                .clickable {
                                    expandedListId = if (expandedListId == entry.list.id) null else entry.list.id
                                },
                        ) {
                            Column(modifier = Modifier.padding(12.dp)) {
                                val dateText = entry.list.completedAt?.let { dateFormat.format(Date(it)) } ?: "—"
                                Text(dateText, fontWeight = FontWeight.Bold)
                                Text("План ${formatMoney(entry.list.plannedTotal)} · Факт ${formatMoney(entry.actualTotal)}")

                                AnimatedVisibility(visible = expandedListId == entry.list.id) {
                                    val items by viewModel.itemsFlow(entry.list.id).collectAsState(initial = emptyList())
                                    Column(modifier = Modifier.padding(top = 8.dp)) {
                                        items.forEach { item ->
                                            Text("• ${item.name} (${item.quantity})" + (item.actualPrice?.let { " — ${formatMoney(it)}" } ?: ""))
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
