package com.dividinghead.calculator.ui.screens.helical

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.dividinghead.calculator.ui.components.AccuracyBadge
import com.dividinghead.calculator.ui.components.GearTrainCanvas
import com.dividinghead.calculator.viewmodel.AppViewModelFactory
import com.dividinghead.calculator.viewmodel.HelicalIndexingViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HelicalIndexingScreen(factory: AppViewModelFactory, onBack: () -> Unit) {
    val viewModel: HelicalIndexingViewModel = viewModel(factory = factory)
    val state by viewModel.uiState.collectAsState()

    LaunchedEffect(state.preset) {
        state.preset?.let { viewModel.initPitchFromPreset(it.leadScrewPitchMm) }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Винтовое деление") },
                navigationIcon = {
                    IconButton(onClick = onBack) { Icon(Icons.Filled.ArrowBack, contentDescription = "Назад") }
                }
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(16.dp)
                .verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            Text("Пресет: ${state.presetName}", style = MaterialTheme.typography.bodyMedium)

            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                FilterChip(selected = !state.useInches, onClick = { viewModel.onUnitToggle(false) }, label = { Text("мм") })
                FilterChip(selected = state.useInches, onClick = { viewModel.onUnitToggle(true) }, label = { Text("дюймы") })
            }

            OutlinedTextField(
                value = state.leadText,
                onValueChange = viewModel::onLeadChanged,
                label = { Text("Шаг спирали T, ${if (state.useInches) "in" else "мм"}") },
                keyboardOptions = androidx.compose.foundation.text.KeyboardOptions(keyboardType = KeyboardType.Decimal),
                modifier = Modifier.fillMaxWidth()
            )
            OutlinedTextField(
                value = state.pitchText,
                onValueChange = viewModel::onPitchChanged,
                label = { Text("Шаг ходового винта стола Pв, ${if (state.useInches) "in" else "мм"}") },
                keyboardOptions = androidx.compose.foundation.text.KeyboardOptions(keyboardType = KeyboardType.Decimal),
                modifier = Modifier.fillMaxWidth()
            )
            OutlinedTextField(
                value = state.diameterText,
                onValueChange = viewModel::onDiameterChanged,
                label = { Text("Диаметр заготовки (необязательно), ${if (state.useInches) "in" else "мм"}") },
                keyboardOptions = androidx.compose.foundation.text.KeyboardOptions(keyboardType = KeyboardType.Decimal),
                modifier = Modifier.fillMaxWidth()
            )

            Button(onClick = viewModel::calculate, modifier = Modifier.fillMaxWidth()) {
                Text("Рассчитать")
            }

            state.errorMessage?.let { Text(it, color = MaterialTheme.colorScheme.error) }

            state.result?.let { result ->
                Card(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        result.tableSwivelAngleDeg?.let {
                            Text("Угол разворота стола: ${"%.2f".format(it)}°", style = MaterialTheme.typography.headlineSmall)
                        }
                        result.bestLeadError?.let { err ->
                            Text(
                                "Достигаемый шаг: ${"%.4f".format(err.achievedLeadMm)} " +
                                    "(ошибка ${"%.4f".format(err.errorMm)}, ${"%.3f".format(err.errorPercent)}%)",
                                style = MaterialTheme.typography.bodyMedium
                            )
                        }
                    }
                }

                Text("Шестерни гитары:", style = MaterialTheme.typography.titleMedium)
                result.gearChoices.forEachIndexed { index, combo ->
                    Card(Modifier.fillMaxWidth()) {
                        Column(Modifier.padding(16.dp)) {
                            val gearText = if (combo.isCompound)
                                "A=${combo.driver1}  B=${combo.driven1}  C=${combo.driver2}  D=${combo.driven2}"
                            else
                                "A=${combo.driver1}  B=${combo.driven1}"
                            Text(gearText, style = MaterialTheme.typography.titleSmall)
                            Text(
                                "Погрешность передаточного отношения: ${"%.3f".format(combo.errorPercent)}%",
                                style = MaterialTheme.typography.bodySmall
                            )
                            if (!combo.feasible) {
                                Text(
                                    "⚠ Возможна коллизия шестерён на общей оси",
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.error
                                )
                            }
                            GearTrainCanvas(
                                driver1 = combo.driver1,
                                driven1 = combo.driven1,
                                driver2 = combo.driver2,
                                driven2 = combo.driven2
                            )
                        }
                    }
                    if (index == 0) {
                        AccuracyBadge(
                            exact = combo.exact,
                            errorDescription = if (!combo.exact)
                                "Ошибка шага спирали: ${"%.3f".format(result.bestLeadError?.errorPercent ?: 0.0)}%" else null
                        )
                    }
                }
            }
        }
    }
}
