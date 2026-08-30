package com.robutpit.roachrace.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.size
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.rotate
import androidx.compose.ui.unit.dp
import kotlin.math.cos
import kotlin.math.sin

private val outline = Color(0xFF1A140D)

/** Draws one stylised roach: an oval body, a smaller head, three pairs of
 * legs and two antennae, all scaled by [sizePx]. Shared by the breed/colour
 * picker preview, the training gym and the live race canvas so the same
 * silhouette is used everywhere. [legPhase] animates the legs; [wobble]
 * tilts the body; [headingDegrees] points the head in the direction of
 * travel — 0 faces left (the gym's default), 90 faces up (the vertical
 * race track). */
fun DrawScope.drawRoach(center: Offset, sizePx: Float, color: Color, legPhase: Float, wobble: Float, headingDegrees: Float = 0f) {
    val s = sizePx
    rotate(degrees = wobble * 12f + headingDegrees, pivot = center) {
        val legWave = sin(legPhase) * (s * 0.16f)
        val legOffsets = floatArrayOf(-0.15f, 0.25f, 0.6f)
        legOffsets.forEachIndexed { idx, lx ->
            val w = if (idx % 2 == 0) legWave else -legWave
            drawLine(outline, Offset(center.x + lx * s, center.y - s * 0.5f), Offset(center.x + lx * s - s * 0.3f, center.y - s * 1.0f - w), strokeWidth = s * 0.07f)
            drawLine(outline, Offset(center.x + lx * s, center.y + s * 0.5f), Offset(center.x + lx * s - s * 0.3f, center.y + s * 1.0f + w), strokeWidth = s * 0.07f)
        }
        drawLine(outline, Offset(center.x - s * 0.9f, center.y - s * 0.15f), Offset(center.x - s * 1.5f, center.y - s * 0.6f - legWave), strokeWidth = s * 0.08f)
        drawLine(outline, Offset(center.x - s * 0.9f, center.y + s * 0.15f), Offset(center.x - s * 1.5f, center.y + s * 0.6f + legWave), strokeWidth = s * 0.08f)

        drawOval(color, topLeft = Offset(center.x - s, center.y - s * 0.6f), size = androidx.compose.ui.geometry.Size(s * 2f, s * 1.2f))
        drawOval(outline, topLeft = Offset(center.x - s, center.y - s * 0.6f), size = androidx.compose.ui.geometry.Size(s * 2f, s * 1.2f), style = Stroke(s * 0.06f))

        val headCenter = Offset(center.x - s * 0.55f, center.y)
        drawOval(color, topLeft = Offset(headCenter.x - s * 0.42f, headCenter.y - s * 0.4f), size = androidx.compose.ui.geometry.Size(s * 0.84f, s * 0.8f))
        drawOval(outline, topLeft = Offset(headCenter.x - s * 0.42f, headCenter.y - s * 0.4f), size = androidx.compose.ui.geometry.Size(s * 0.84f, s * 0.8f), style = Stroke(s * 0.05f))
    }
}

@Composable
fun RoachPreview(sizeDp: Int, color: Color, wobble: Float = 0f) {
    Canvas(modifier = Modifier.size(sizeDp.dp)) {
        val s = kotlin.math.min(size.width, size.height) * 0.22f
        drawRoach(Offset(size.width / 2f, size.height / 2f), s, color, legPhase = cos(0f), wobble = wobble)
    }
}
