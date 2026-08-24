package com.dividinghead.calculator.ui.screens.history

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.DeleteSweep
import androidx.compose.material3.Card
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.dividinghead.calculator.viewmodel.AppViewModelFactory
import com.dividinghead.calculator.viewmodel.HistoryViewModel
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HistoryScreen(factory: AppViewModelFactory, onBack: () -> Unit) {
    val viewModel: HistoryViewModel = viewModel(factory = factory)
    val history by viewModel.history.collectAsState()
    val formatter = remember(Unit) { SimpleDateFormat("dd.MM.yyyy HH:mm", Locale("ru")) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("История расчётов") },
                navigationIcon = {
                    IconButton(onClick = onBack) { Icon(Icons.Filled.ArrowBack, contentDescription = "Назад") }
                },
                actions = {
                    IconButton(onClick = viewModel::clear) {
                        Icon(Icons.Filled.DeleteSweep, contentDescription = "Очистить историю")
                    }
                }
            )
        }
    ) { padding ->
        if (history.isEmpty()) {
            Column(
                Modifier.fillMaxSize().padding(padding),
            ) {
                Text(
                    "История пуста. Выполненные расчёты появятся здесь.",
                    modifier = Modifier.padding(24.dp)
                )
            }
        } else {
            LazyColumn(
                modifier = Modifier.fillMaxSize().padding(padding).padding(horizontal = 16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                items(history, key = { it.id }) { entry ->
                    Card(Modifier.fillMaxWidth()) {
                        Row(
                            Modifier.fillMaxWidth().padding(12.dp),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column(Modifier.weight(1f)) {
                                Text(entry.mode, style = MaterialTheme.typography.titleSmall)
                                Text(entry.summary, style = MaterialTheme.typography.bodyMedium)
                                Text(entry.details, style = MaterialTheme.typography.bodySmall)
                                Text(
                                    formatter.format(Date(entry.timestamp)),
                                    style = MaterialTheme.typography.labelSmall,
                                    color = MaterialTheme.colorScheme.outline
                                )
                            }
                            IconButton(onClick = { viewModel.delete(entry) }) {
                                Icon(Icons.Filled.Delete, contentDescription = "Удалить запись")
                            }
                        }
                    }
                }
            }
        }
    }
}
