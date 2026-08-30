package com.robutpit.zamri.ui.components

import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import com.robutpit.zamri.R
import androidx.compose.ui.res.stringResource
import kotlin.math.min

/**
 * Original, non-derivative doll referee mark: a simple round-headed figure
 * with pigtail bows that spins 180° between "facing away" (green light -
 * players may move) and "facing the players" (red light - freeze). Uses a
 * card-flip style rotationY so the turn genuinely reads as a 180° pivot
 * rather than a cross-fade.
 */
@Composable
fun DollFigure(
    facingPlayers: Boolean,
    isWatching: Boolean,
    modifier: Modifier = Modifier
) {
    val rotation by animateFloatAsState(
        targetValue = if (facingPlayers) 180f else 0f,
        animationSpec = tween(durationMillis = 650),
        label = "dollRotation"
    )
    val density = LocalDensity.current

    val alertPulse by rememberInfiniteTransition(label = "alertPulse").animateFloat(
        initialValue = 0f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(
            animation = tween(900, easing = LinearEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "alertPulseAnim"
    )

    val dollContentDescription = stringResource(R.string.cd_doll)
    Box(
        modifier
            .aspectRatio(1f)
            .semantics { contentDescription = dollContentDescription }
            .graphicsLayer {
                rotationY = rotation
                cameraDistance = 12f * density.density
            }
    ) {
        if (rotation <= 90f) {
            DollCanvas(showFace = false, alertPulse = 0f)
        } else {
            Box(Modifier.graphicsLayer { rotationY = 180f }) {
                DollCanvas(showFace = true, alertPulse = if (isWatching) alertPulse else 0f)
            }
        }
    }
}

@Composable
private fun DollCanvas(showFace: Boolean, alertPulse: Float) {
    val faceColor = Color(0xFFFFE0B2)
    val hairColor = Color(0xFF3E2723)
    val bowColor = Color(0xFFD81B60)
    val bodyColor = Color(0xFF37474F)
    val eyeColor = if (showFace) Color(0xFFE53935) else Color.Transparent

    Canvas(modifier = Modifier.aspectRatio(1f)) {
        val w = size.width
        val h = size.height
        val cx = w / 2f
        val headR = min(w, h) * 0.22f
        val headCy = h * 0.32f

        // Body
        drawRoundRect(
            color = bodyColor,
            topLeft = Offset(cx - w * 0.22f, h * 0.5f),
            size = androidx.compose.ui.geometry.Size(w * 0.44f, h * 0.42f),
            cornerRadius = androidx.compose.ui.geometry.CornerRadius(w * 0.12f, w * 0.12f)
        )

        // Head
        drawCircle(color = faceColor, radius = headR, center = Offset(cx, headCy))

        // Hair / back-of-head shading
        drawCircle(
            color = hairColor,
            radius = headR * 1.05f,
            center = Offset(cx, headCy - headR * 0.35f),
            style = Stroke(width = headR * 0.55f)
        )

        // Pigtail bows
        drawCircle(color = bowColor, radius = headR * 0.28f, center = Offset(cx - headR * 1.15f, headCy - headR * 0.1f))
        drawCircle(color = bowColor, radius = headR * 0.28f, center = Offset(cx + headR * 1.15f, headCy - headR * 0.1f))

        if (showFace) {
            val eyeOffsetX = headR * 0.42f
            val eyeY = headCy - headR * 0.05f
            val eyeR = headR * (0.13f + 0.03f * alertPulse)
            drawCircle(color = eyeColor, radius = eyeR, center = Offset(cx - eyeOffsetX, eyeY))
            drawCircle(color = eyeColor, radius = eyeR, center = Offset(cx + eyeOffsetX, eyeY))
            // Shouting mouth
            drawCircle(
                color = Color(0xFF6D1B1B),
                radius = headR * 0.22f,
                center = Offset(cx, headCy + headR * 0.42f)
            )
        }
    }
}
