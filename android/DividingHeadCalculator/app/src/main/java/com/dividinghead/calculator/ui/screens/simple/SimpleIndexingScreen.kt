package com.dividinghead.calculator.ui.screens.simple

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
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
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.dividinghead.calculator.ui.components.AccuracyBadge
import com.dividinghead.calculator.ui.components.IndexPlateCanvas
import com.dividinghead.calculator.ui.components.formatArcError
import com.dividinghead.calculator.viewmodel.AppViewModelFactory
import com.dividinghead.calculator.viewmodel.SimpleIndexingViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SimpleIndexingScreen(factory: AppViewModelFactory, onBack: () -> Unit) {
    val viewModel: SimpleIndexingViewModel = viewModel(factory = factory)
    val state by viewModel.uiState.collectAsState()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Простое деление") },
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

            OutlinedTextField(
                value = state.nText,
                onValueChange = viewModel::onNChanged,
                label = { Text("Число делений") },
                keyboardOptions = androidx.compose.foundation.text.KeyboardOptions(keyboardType = KeyboardType.Number),
                modifier = Modifier.fillMaxWidth()
            )

            Button(onClick = viewModel::calculate, modifier = Modifier.fillMaxWidth()) {
                Text("Рассчитать")
            }

            state.errorMessage?.let {
                Text(it, color = MaterialTheme.colorScheme.error)
            }

            if (state.alternatives.size > 1) {
                Text("Варианты круга:", style = MaterialTheme.typography.titleSmall)
                LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    items(state.alternatives.size) { index ->
                        val alt = state.alternatives[index]
                        val label = if (alt.hasFraction)
                            "${alt.circleHoles}" + if (alt.exact) " ✓" else " (${"%.2f".format(alt.errorPercentOfStep)}%)"
                        else "без дроби"
                        FilterChip(
                            selected = index == state.selectedIndex,
                            onClick = { viewModel.selectAlternative(index) },
                            label = { Text(label) }
                        )
                    }
                }
            }

            state.result?.let { result ->
                Card(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text("Что крутить:", style = MaterialTheme.typography.titleMedium)
                        if (result.hasFraction) {
                            Text(
                                "${result.wholeTurns} полных оборотов + ${result.holes} отверстий на круге ${result.circleHoles}" +
                                    (result.plateName?.let { " ($it)" } ?: ""),
                                style = MaterialTheme.typography.headlineSmall
                            )
                        } else {
                            Text("${result.wholeTurns} полных оборотов рукоятки", style = MaterialTheme.typography.headlineSmall)
                        }
                    }
                }

                if (result.hasFraction) {
                    IndexPlateCanvas(circleHoles = result.circleHoles, holes = result.holes)
                }

                AccuracyBadge(
                    exact = result.exact,
                    errorDescription = if (!result.exact)
                        formatArcError(result.errorArcSeconds, result.errorPercentOfStep) else null,
                    warningLevel = result.errorPercentOfStep > 5.0
                )
            }
        }
    }
}
