package com.dividinghead.calculator.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.min
import kotlin.math.sin

/**
 * Draws an index (dividing) plate with [circleHoles] holes arranged on a circle, highlighting
 * the [holes] consecutive holes spanning the sector the divider legs should be set to.
 */
@Composable
fun IndexPlateCanvas(
    circleHoles: Int,
    holes: Int,
    modifier: Modifier = Modifier
) {
    val primary = MaterialTheme.colorScheme.primary
    val secondary = MaterialTheme.colorScheme.secondary
    val outline = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.35f)

    Canvas(modifier = modifier.fillMaxWidth().aspectRatio(1f)) {
        if (circleHoles <= 0) return@Canvas
        val radius = min(size.width, size.height) / 2f * 0.82f
        val center = Offset(size.width / 2f, size.height / 2f)

        drawCircle(color = outline, radius = radius, center = center, style = Stroke(width = 3f))

        val holeRadius = radius * 0.045f
        val positions = (0 until circleHoles).map { i ->
            val angle = -PI / 2.0 + 2.0 * PI * i / circleHoles
            Offset(
                x = (center.x + radius * cos(angle)).toFloat(),
                y = (center.y + radius * sin(angle)).toFloat()
            )
        }

        // Highlighted sector (the "opening" of the divider legs)
        if (holes in 1 until circleHoles) {
            val startAngle = -PI / 2.0
            val endAngle = -PI / 2.0 + 2.0 * PI * holes / circleHoles
            drawLine(color = secondary, start = center, end = positions[0], strokeWidth = 5f)
            drawLine(
                color = secondary,
                start = center,
                end = Offset(
                    (center.x + radius * cos(endAngle)).toFloat(),
                    (center.y + radius * sin(endAngle)).toFloat()
                ),
                strokeWidth = 5f
            )
        }

        positions.forEachIndexed { i, p ->
            val highlighted = holes in 1 until circleHoles && i <= holes
            drawCircle(
                color = if (highlighted) secondary else primary,
                radius = holeRadius,
                center = p
            )
        }

        drawCircle(color = outline, radius = radius * 0.03f, center = center)
    }
}
