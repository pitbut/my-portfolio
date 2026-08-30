package com.robutpit.zamri.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.robutpit.zamri.R
import com.robutpit.zamri.ui.GamePhase
import com.robutpit.zamri.ui.GameViewModel
import com.robutpit.zamri.ui.components.CameraFeed
import com.robutpit.zamri.ui.components.CameraPermissionGate
import com.robutpit.zamri.ui.components.DollFigure
import com.robutpit.zamri.ui.components.ViolationOverlay
import com.robutpit.zamri.ui.theme.DollGreen
import com.robutpit.zamri.ui.theme.DollRed

@Composable
fun GameScreen(
    viewModel: GameViewModel,
    onFinished: () -> Unit,
    onOpenArchive: () -> Unit
) {
    val phase by viewModel.phase.collectAsStateWithLifecycle()
    val lastViolation by viewModel.lastViolation.collectAsStateWithLifecycle()

    LaunchedEffect(Unit) { viewModel.startGame() }

    Box(Modifier.fillMaxSize()) {
        CameraPermissionGate {
            CameraFeed(motionDetector = viewModel.motionDetector, modifier = Modifier.fillMaxSize())

            Box(
                Modifier
                    .fillMaxSize()
                    .background(Color.Black.copy(alpha = 0.35f))
            )

            when (val p = phase) {
                is GamePhase.Idle -> {}
                is GamePhase.Countdown -> CountdownContent(p)
                is GamePhase.Green -> PhaseContent(
                    facingPlayers = false,
                    isWatching = false,
                    title = stringResource(R.string.phase_green),
                    hint = stringResource(R.string.phase_green_hint),
                    accent = DollGreen,
                    elapsed = p.gameElapsedSec,
                    total = p.totalGameSec,
                    onFinish = { viewModel.finishGame() }
                )
                is GamePhase.Red -> PhaseContent(
                    facingPlayers = true,
                    isWatching = true,
                    title = stringResource(R.string.phase_red),
                    hint = stringResource(R.string.phase_red_hint),
                    accent = DollRed,
                    elapsed = p.gameElapsedSec,
                    total = p.totalGameSec,
                    onFinish = { viewModel.finishGame() }
                )
                is GamePhase.Result -> ResultContent(
                    result = p,
                    onNewGame = { viewModel.startGame() },
                    onArchive = onOpenArchive,
                    onHome = onFinished
                )
            }

            ViolationOverlay(event = lastViolation, modifier = Modifier.fillMaxSize())
        }
    }
}

@Composable
private fun CountdownContent(phase: GamePhase.Countdown) {
    Column(
        Modifier.fillMaxSize(),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Text(stringResource(R.string.countdown_title), color = Color.White, style = MaterialTheme.typography.headlineMedium)
        Text(
            text = phase.secondsLeft.toString(),
            color = Color.White,
            fontSize = 96.sp,
            fontWeight = FontWeight.Bold
        )
        Text(stringResource(R.string.countdown_hint), color = Color.White.copy(alpha = 0.8f))
    }
}

@Composable
private fun PhaseContent(
    facingPlayers: Boolean,
    isWatching: Boolean,
    title: String,
    hint: String,
    accent: Color,
    elapsed: Int,
    total: Int,
    onFinish: () -> Unit
) {
    Column(Modifier.fillMaxSize().padding(24.dp)) {
        PhaseHeader(elapsed, total, accent)

        Spacer(Modifier.weight(1f))

        DollFigure(
            facingPlayers = facingPlayers,
            isWatching = isWatching,
            modifier = Modifier.fillMaxWidth(0.6f).align(Alignment.CenterHorizontally)
        )

        Column(
            Modifier.align(Alignment.CenterHorizontally),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(
                title,
                color = accent,
                fontSize = 34.sp,
                fontWeight = FontWeight.Bold,
                modifier = Modifier.padding(top = 16.dp)
            )
            Text(hint, color = Color.White, style = MaterialTheme.typography.titleMedium)
        }

        Spacer(Modifier.weight(1f))

        OutlinedButton(
            onClick = onFinish,
            modifier = Modifier.fillMaxWidth().height(56.dp),
            colors = ButtonDefaults.outlinedButtonColors(contentColor = Color.White)
        ) {
            Text(stringResource(R.string.finish_button))
        }
    }
}

@Composable
private fun PhaseHeader(elapsed: Int, total: Int, accent: Color) {
    Row(
        Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            Modifier
                .size(14.dp)
                .clip(CircleShape)
                .background(accent)
        )
        Text(
            text = "$elapsed / $total с",
            color = Color.White,
            style = MaterialTheme.typography.labelLarge
        )
    }
}

@Composable
private fun ResultContent(
    result: GamePhase.Result,
    onNewGame: () -> Unit,
    onArchive: () -> Unit,
    onHome: () -> Unit
) {
    Column(
        Modifier.fillMaxSize().padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Text(
            stringResource(R.string.result_title),
            color = Color.White,
            fontSize = 32.sp,
            fontWeight = FontWeight.Bold
        )
        Spacer(Modifier.height(16.dp))
        Text(
            stringResource(R.string.result_rounds, result.roundsPlayed),
            color = Color.White,
            style = MaterialTheme.typography.titleLarge
        )
        Text(
            stringResource(R.string.result_violations, result.violationsCount),
            color = DollRed,
            style = MaterialTheme.typography.titleLarge
        )

        Spacer(Modifier.height(32.dp))

        Button(onClick = onNewGame, modifier = Modifier.fillMaxWidth().height(56.dp)) {
            Text(stringResource(R.string.result_new_game))
        }
        Spacer(Modifier.height(12.dp))
        OutlinedButton(
            onClick = onArchive,
            modifier = Modifier.fillMaxWidth().height(56.dp),
            colors = ButtonDefaults.outlinedButtonColors(contentColor = Color.White)
        ) {
            Text(stringResource(R.string.result_to_archive))
        }
        Spacer(Modifier.height(12.dp))
        OutlinedButton(
            onClick = onHome,
            modifier = Modifier.fillMaxWidth().height(56.dp),
            colors = ButtonDefaults.outlinedButtonColors(contentColor = Color.White)
        ) {
            Text(stringResource(R.string.cd_back))
        }
    }
}
