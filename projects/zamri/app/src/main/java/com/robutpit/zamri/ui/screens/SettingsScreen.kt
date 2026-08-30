package com.robutpit.zamri.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Slider
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.robutpit.zamri.R
import com.robutpit.zamri.data.GameSettings
import com.robutpit.zamri.ui.GameViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(viewModel: GameViewModel, onBack: () -> Unit) {
    val settings by viewModel.settings.collectAsStateWithLifecycle()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(stringResource(R.string.settings_title)) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = stringResource(R.string.cd_back))
                    }
                }
            )
        }
    ) { padding ->
        Column(
            Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 24.dp)
                .verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(20.dp)
        ) {
            SettingsSliderRow(
                label = stringResource(R.string.settings_round_duration),
                value = settings.roundDurationSec,
                valueRange = 30f..600f,
                valueText = "${settings.roundDurationSec} с",
                onChange = { viewModel.updateSettings(settings.copy(roundDurationSec = it)) }
            )

            Text(stringResource(R.string.settings_green_range), style = MaterialTheme.typography.titleMedium)
            SettingsSliderRow(
                label = "min",
                value = settings.greenMinSec,
                valueRange = 1f..30f,
                valueText = "${settings.greenMinSec} с",
                onChange = { v ->
                    viewModel.updateSettings(
                        settings.copy(
                            greenMinSec = v,
                            greenMaxSec = maxOf(v, settings.greenMaxSec)
                        )
                    )
                }
            )
            SettingsSliderRow(
                label = "max",
                value = settings.greenMaxSec,
                valueRange = 1f..30f,
                valueText = "${settings.greenMaxSec} с",
                onChange = { v ->
                    viewModel.updateSettings(
                        settings.copy(
                            greenMaxSec = v,
                            greenMinSec = minOf(v, settings.greenMinSec)
                        )
                    )
                }
            )

            SettingsSliderRow(
                label = stringResource(R.string.settings_red_duration),
                value = settings.redFreezeSec,
                valueRange = 1f..15f,
                valueText = "${settings.redFreezeSec} с",
                onChange = { viewModel.updateSettings(settings.copy(redFreezeSec = it)) }
            )

            SettingsSliderRow(
                label = stringResource(R.string.settings_sectors),
                value = settings.sectorCount,
                valueRange = GameSettings.MIN_SECTORS.toFloat()..GameSettings.MAX_SECTORS.toFloat(),
                valueText = "${settings.sectorCount}",
                onChange = { viewModel.updateSettings(settings.copy(sectorCount = it)) }
            )

            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(stringResource(R.string.settings_sound_enabled), style = MaterialTheme.typography.titleMedium)
                Switch(
                    checked = settings.soundEnabled,
                    onCheckedChange = { viewModel.updateSettings(settings.copy(soundEnabled = it)) }
                )
            }

            SettingsSliderRow(
                label = stringResource(R.string.settings_volume),
                value = settings.volumePercent,
                valueRange = 0f..100f,
                valueText = "${settings.volumePercent}%",
                onChange = { viewModel.updateSettings(settings.copy(volumePercent = it)) }
            )

            SettingsSliderRow(
                label = stringResource(R.string.settings_sensitivity),
                value = settings.sensitivityPercent,
                valueRange = 0f..100f,
                valueText = "${settings.sensitivityPercent}%",
                onChange = { viewModel.updateSettings(settings.copy(sensitivityPercent = it)) }
            )

            Button(onClick = onBack, modifier = Modifier.fillMaxWidth().padding(vertical = 24.dp)) {
                Text(stringResource(R.string.settings_back))
            }
        }
    }
}

@Composable
private fun SettingsSliderRow(
    label: String,
    value: Int,
    valueRange: ClosedFloatingPointRange<Float>,
    valueText: String,
    onChange: (Int) -> Unit
) {
    Column {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Text(label, style = MaterialTheme.typography.bodyLarge)
            Text(valueText, style = MaterialTheme.typography.bodyLarge)
        }
        Slider(
            value = value.toFloat(),
            valueRange = valueRange,
            onValueChange = { onChange(it.toInt()) }
        )
    }
}
