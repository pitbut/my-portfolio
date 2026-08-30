package com.robutpit.zamri.ui.components

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.robutpit.zamri.R
import com.robutpit.zamri.data.db.ViolationSide
import com.robutpit.zamri.ui.ViolationUiEvent

/** Semi-transparent 2-3s callout shown right after the detector catches motion. */
@Composable
fun ViolationOverlay(event: ViolationUiEvent?, modifier: Modifier = Modifier) {
    AnimatedVisibility(
        visible = event != null,
        enter = fadeIn(),
        exit = fadeOut(),
        modifier = modifier
    ) {
        if (event == null) return@AnimatedVisibility
        Box(
            Modifier
                .fillMaxSize()
                .background(Color.Black.copy(alpha = 0.55f)),
            contentAlignment = Alignment.Center
        ) {
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                modifier = Modifier
                    .padding(24.dp)
                    .clip(RoundedCornerShape(16.dp))
                    .background(MaterialTheme.colorScheme.surface)
                    .padding(16.dp)
            ) {
                Text(
                    text = stringResource(R.string.violation_caught),
                    style = MaterialTheme.typography.headlineSmall,
                    color = MaterialTheme.colorScheme.tertiary
                )
                Image(
                    bitmap = event.markedPhoto.asImageBitmap(),
                    contentDescription = stringResource(R.string.cd_photo_thumbnail),
                    modifier = Modifier
                        .padding(top = 12.dp)
                        .size(220.dp)
                        .clip(RoundedCornerShape(12.dp))
                )
                Text(
                    text = sideLabel(event.label.side, event.label.sideLane),
                    style = MaterialTheme.typography.titleLarge,
                    modifier = Modifier.padding(top = 12.dp)
                )
            }
        }
    }
}

@Composable
fun sideLabel(side: ViolationSide, sideLane: Int): String {
    val sideWord = when (side) {
        ViolationSide.LEFT -> stringResource(R.string.side_left)
        ViolationSide.RIGHT -> stringResource(R.string.side_right)
        ViolationSide.CENTER -> stringResource(R.string.side_center)
    }
    return if (side == ViolationSide.CENTER) sideWord else "$sideWord, $sideLane"
}
