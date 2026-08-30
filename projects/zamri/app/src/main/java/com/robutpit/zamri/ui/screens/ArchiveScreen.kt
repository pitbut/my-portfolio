package com.robutpit.zamri.ui.screens

import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.Card
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import coil.compose.AsyncImage
import com.robutpit.zamri.R
import com.robutpit.zamri.data.db.ViolationEntity
import com.robutpit.zamri.ui.ArchiveViewModel
import com.robutpit.zamri.ui.components.sideLabel
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ArchiveScreen(viewModel: ArchiveViewModel, onBack: () -> Unit) {
    val violations by viewModel.filteredViolations.collectAsStateWithLifecycle()
    val rounds by viewModel.availableRounds.collectAsStateWithLifecycle()
    val selectedRound by viewModel.selectedRound.collectAsStateWithLifecycle()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(stringResource(R.string.archive_title)) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = stringResource(R.string.cd_back))
                    }
                }
            )
        }
    ) { padding ->
        Column(Modifier.fillMaxSize().padding(padding)) {
            Row(
                Modifier
                    .fillMaxWidth()
                    .horizontalScroll(rememberScrollState())
                    .padding(horizontal = 16.dp, vertical = 8.dp),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                FilterChip(
                    selected = selectedRound == null,
                    onClick = { viewModel.selectRound(null) },
                    label = { Text(stringResource(R.string.archive_round_all)) }
                )
                val roundLabel = stringResource(R.string.archive_round_filter)
                rounds.forEach { round ->
                    FilterChip(
                        selected = selectedRound == round,
                        onClick = { viewModel.selectRound(round) },
                        label = { Text("$roundLabel $round") }
                    )
                }
            }

            if (violations.isEmpty()) {
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Text(
                        stringResource(R.string.archive_empty),
                        color = MaterialTheme.colorScheme.onBackground.copy(alpha = 0.6f)
                    )
                }
            } else {
                LazyVerticalGrid(
                    columns = GridCells.Fixed(2),
                    contentPadding = PaddingValues(12.dp),
                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    items(violations, key = { it.id }) { violation ->
                        ViolationCard(violation)
                    }
                }
            }
        }
    }
}

@Composable
private fun ViolationCard(violation: ViolationEntity) {
    Card(Modifier.fillMaxWidth()) {
        Column {
            AsyncImage(
                model = violation.photoUri,
                contentDescription = stringResource(R.string.cd_photo_thumbnail),
                modifier = Modifier.fillMaxWidth().aspectRatio(1f),
                contentScale = ContentScale.Crop
            )
            Text(
                text = stringResource(
                    R.string.archive_item_format,
                    violation.round,
                    sideLabel(violation.side, violation.sideLane),
                    formatTime(violation.timestampMillis)
                ),
                style = MaterialTheme.typography.bodySmall,
                modifier = Modifier.padding(8.dp)
            )
        }
    }
}

private val TIME_FORMAT = SimpleDateFormat("HH:mm:ss", Locale.getDefault())

private fun formatTime(millis: Long): String = TIME_FORMAT.format(Date(millis))
