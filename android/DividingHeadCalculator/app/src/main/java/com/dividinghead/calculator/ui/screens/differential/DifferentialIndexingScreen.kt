package com.dividinghead.calculator.ui.screens.differential

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
import com.dividinghead.calc.PlateRotationDirection
import com.dividinghead.calculator.ui.components.AccuracyBadge
import com.dividinghead.calculator.ui.components.GearTrainCanvas
import com.dividinghead.calculator.ui.components.IndexPlateCanvas
import com.dividinghead.calculator.viewmodel.AppViewModelFactory
import com.dividinghead.calculator.viewmodel.DifferentialIndexingViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DifferentialIndexingScreen(factory: AppViewModelFactory, onBack: () -> Unit) {
    val viewModel: DifferentialIndexingViewModel = viewModel(factory = factory)
    val state by viewModel.uiState.collectAsState()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Дифференциальное деление") },
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

            Button(onClick = viewModel::findAndCalculate, modifier = Modifier.fillMaxWidth()) {
                Text("Подобрать n' и рассчитать")
            }

            state.errorMessage?.let { Text(it, color = MaterialTheme.colorScheme.error) }

            if (state.candidates.size > 1) {
                Text("Вспомогательное число n':", style = MaterialTheme.typography.titleSmall)
                LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    items(state.candidates) { candidate ->
                        FilterChip(
                            selected = candidate == state.selectedAux,
                            onClick = { viewModel.selectAux(candidate) },
                            label = { Text(candidate.toString()) }
                        )
                    }
                }
            }

            state.result?.let { result ->
                Card(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text("Раствор циркуля (по n'=${result.auxiliaryDivisions}):", style = MaterialTheme.typography.titleMedium)
                        val plate = result.plateIndexing
                        val plateText = if (plate.hasFraction)
                            "${plate.wholeTurns} об. + ${plate.holes} отв. на круге ${plate.circleHoles}"
                        else "${plate.wholeTurns} полных оборотов"
                        Text(plateText, style = MaterialTheme.typography.headlineSmall)

                        Text(
                            "Направление вращения диска: " + when (result.direction) {
                                PlateRotationDirection.SAME_AS_CRANK -> "то же, что и у рукоятки"
                                PlateRotationDirection.OPPOSITE_TO_CRANK -> "противоположное рукоятке"
                            },
                            style = MaterialTheme.typography.bodyMedium
                        )
                    }
                }

                if (result.plateIndexing.hasFraction) {
                    IndexPlateCanvas(circleHoles = result.plateIndexing.circleHoles, holes = result.plateIndexing.holes)
                }

                if (result.gearChoices.size > 1) {
                    Text("Варианты шестерён гитары:", style = MaterialTheme.typography.titleSmall)
                    LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        items(result.gearChoices.size) { index ->
                            val c = result.gearChoices[index].combination
                            val label = (if (c.isCompound) "${c.driver1}/${c.driven1}·${c.driver2}/${c.driven2}" else "${c.driver1}/${c.driven1}") +
                                if (c.exact) " ✓" else " (${"%.2f".format(c.errorPercent)}%)"
                            FilterChip(
                                selected = index == state.selectedGearIndex,
                                onClick = { viewModel.selectGear(index) },
                                label = { Text(label) }
                            )
                        }
                    }
                }

                state.selectedGearChoice?.let { choice ->
                    val combo = choice.combination
                    Card(Modifier.fillMaxWidth()) {
                        Column(Modifier.padding(16.dp)) {
                            val gearText = if (combo.isCompound)
                                "A=${combo.driver1}  B=${combo.driven1}  C=${combo.driver2}  D=${combo.driven2}"
                            else
                                "A=${combo.driver1}  B=${combo.driven1}"
                            Text(gearText, style = MaterialTheme.typography.titleSmall)
                            Text(
                                "Погрешность: ${"%.3f".format(combo.errorPercent)}%" +
                                    if (choice.idlerRequired) " • нужна паразитная шестерня" else "",
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
                    AccuracyBadge(
                        exact = combo.exact,
                        errorDescription = if (!combo.exact) "Погрешность передаточного отношения: ${"%.3f".format(combo.errorPercent)}%" else null
                    )
                }
            }
        }
    }
}
