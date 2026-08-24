package com.dividinghead.calculator.ui.screens.headsettings

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
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Divider
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Switch
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
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.dividinghead.calculator.data.datastore.ThemeMode
import com.dividinghead.calculator.data.datastore.UnitSystem
import com.dividinghead.calculator.viewmodel.AppViewModelFactory
import com.dividinghead.calculator.viewmodel.PresetViewModel
import com.dividinghead.calculator.viewmodel.SettingsViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HeadSettingsScreen(
    factory: AppViewModelFactory,
    onBack: () -> Unit
) {
    val presetViewModel: PresetViewModel = viewModel(factory = factory)
    val settingsViewModel: SettingsViewModel = viewModel(factory = factory)
    val presetState by presetViewModel.uiState.collectAsState()
    val settings by settingsViewModel.settings.collectAsState()

    var showNewPresetForm by remember { mutableStateOf(false) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Настройки головки") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Filled.ArrowBack, contentDescription = "Назад")
                    }
                }
            )
        }
    ) { padding ->
        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(padding).padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            item { Text("Пресет головки", style = MaterialTheme.typography.titleMedium) }
            items(presetState.allPresets) { identified ->
                Card(
                    onClick = { presetViewModel.selectPreset(identified.id) },
                    colors = CardDefaults.cardColors(
                        containerColor = if (identified.id == presetState.selectedId)
                            MaterialTheme.colorScheme.primaryContainer
                        else MaterialTheme.colorScheme.surfaceVariant
                    ),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Row(
                        Modifier.fillMaxWidth().padding(12.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Column(Modifier.weight(1f)) {
                            Text(identified.preset.name, style = MaterialTheme.typography.titleSmall)
                            Text(
                                "N=${identified.preset.characteristicN}, кругов: ${identified.preset.plateSet.allCircles.size}, шестерён: ${identified.preset.gearSet.gears.size}",
                                style = MaterialTheme.typography.bodySmall
                            )
                        }
                        RadioButton(
                            selected = identified.id == presetState.selectedId,
                            onClick = { presetViewModel.selectPreset(identified.id) }
                        )
                        if (!identified.isBuiltIn) {
                            IconButton(onClick = { presetViewModel.deleteCustomPreset(identified) }) {
                                Icon(Icons.Filled.Delete, contentDescription = "Удалить пресет")
                            }
                        }
                    }
                }
            }
            item {
                Button(onClick = { showNewPresetForm = !showNewPresetForm }, modifier = Modifier.fillMaxWidth()) {
                    Text(if (showNewPresetForm) "Скрыть форму" else "Создать свой пресет")
                }
            }
            if (showNewPresetForm) {
                item {
                    NewPresetForm(onSave = { name, n, circles, gears, pitch, metric ->
                        presetViewModel.saveCustomPreset(name, n, circles, gears, pitch, metric)
                        showNewPresetForm = false
                    })
                }
            }

            item { Divider(Modifier.padding(vertical = 8.dp)) }

            item { Text("Оформление", style = MaterialTheme.typography.titleMedium) }
            item {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    listOf(
                        ThemeMode.SYSTEM to "Системная",
                        ThemeMode.LIGHT to "Светлая",
                        ThemeMode.DARK to "Тёмная"
                    ).forEach { (mode, label) ->
                        FilterChip(
                            selected = settings.themeMode == mode,
                            onClick = { settingsViewModel.setThemeMode(mode) },
                            label = { Text(label) }
                        )
                    }
                }
            }
            item {
                Row(
                    Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column {
                        Text("Увеличенный шрифт для цеха")
                        Text(
                            "Крупный текст для работы у станка",
                            style = MaterialTheme.typography.bodySmall
                        )
                    }
                    Switch(
                        checked = settings.largeFontForShop,
                        onCheckedChange = { settingsViewModel.setLargeFontForShop(it) }
                    )
                }
            }
            item {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    listOf(
                        UnitSystem.METRIC to "Метрическая",
                        UnitSystem.IMPERIAL to "Дюймовая"
                    ).forEach { (system, label) ->
                        FilterChip(
                            selected = settings.unitSystem == system,
                            onClick = { settingsViewModel.setUnitSystem(system) },
                            label = { Text(label) }
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun NewPresetForm(
    onSave: (name: String, n: Int, circles: List<Int>, gears: List<Int>, pitch: Double, metric: Boolean) -> Unit
) {
    var name by remember { mutableStateOf("") }
    var n by remember { mutableStateOf("40") }
    var circles by remember { mutableStateOf("15,16,17,18,19,20,21,23,27,29,31,33") }
    var gears by remember { mutableStateOf("24,28,32,40,44,48,56,64,72,86,100") }
    var pitch by remember { mutableStateOf("6.0") }
    var metric by remember { mutableStateOf(true) }

    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedTextField(value = name, onValueChange = { name = it }, label = { Text("Название пресета") }, modifier = Modifier.fillMaxWidth())
            OutlinedTextField(value = n, onValueChange = { n = it.filter(Char::isDigit) }, label = { Text("Характеристика головки N") }, modifier = Modifier.fillMaxWidth())
            OutlinedTextField(value = circles, onValueChange = { circles = it }, label = { Text("Круги отверстий (через запятую)") }, modifier = Modifier.fillMaxWidth())
            OutlinedTextField(value = gears, onValueChange = { gears = it }, label = { Text("Шестерни гитары (через запятую)") }, modifier = Modifier.fillMaxWidth())
            OutlinedTextField(value = pitch, onValueChange = { pitch = it }, label = { Text("Шаг ходового винта, мм") }, modifier = Modifier.fillMaxWidth())
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("Метрическая головка")
                Switch(checked = metric, onCheckedChange = { metric = it })
            }
            Button(
                onClick = {
                    val nInt = n.toIntOrNull() ?: 40
                    val circleList = circles.split(",").mapNotNull { it.trim().toIntOrNull() }
                    val gearList = gears.split(",").mapNotNull { it.trim().toIntOrNull() }
                    val pitchVal = pitch.toDoubleOrNull() ?: 6.0
                    if (name.isNotBlank() && circleList.isNotEmpty() && gearList.isNotEmpty()) {
                        onSave(name, nInt, circleList, gearList, pitchVal, metric)
                    }
                },
                modifier = Modifier.fillMaxWidth()
            ) {
                Text("Сохранить пресет")
            }
        }
    }
}
