package com.dividinghead.calculator.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.nativeCanvas
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp
import android.graphics.Paint
import kotlin.math.max
import kotlin.math.min

/**
 * Schematic of the change-gear ("gitara") train: driver1 meshes with driven1; if a second pair
 * is present, driven1's shaft carries driver2 (compound/stud gear), which meshes with driven2.
 */
@Composable
fun GearTrainCanvas(
    driver1: Int,
    driven1: Int,
    driver2: Int? = null,
    driven2: Int? = null,
    modifier: Modifier = Modifier
) {
    val primary = MaterialTheme.colorScheme.primary
    val secondary = MaterialTheme.colorScheme.secondary
    val onSurface = MaterialTheme.colorScheme.onSurface

    val gears = if (driver2 != null && driven2 != null) {
        listOf("A" to driver1, "B" to driven1, "C" to driver2, "D" to driven2)
    } else {
        listOf("A" to driver1, "B" to driven1)
    }

    Canvas(modifier = modifier.fillMaxWidth().aspectRatio(2.2f)) {
        val maxTeeth = gears.maxOf { it.second }.coerceAtLeast(1)
        val minRadius = size.height * 0.16f
        val maxRadius = size.height * 0.34f
        val spacing = size.width / (gears.size + 1)
        val cy = size.height / 2f

        fun radiusFor(teeth: Int): Float {
            val t = teeth.toFloat() / maxTeeth
            return minRadius + (maxRadius - minRadius) * t
        }

        val centers = gears.mapIndexed { index, (_, teeth) ->
            Offset((index + 1) * spacing, cy)
        }

        // mesh lines between consecutive gears
        for (i in 0 until centers.size - 1) {
            drawLine(
                color = onSurface.copy(alpha = 0.3f),
                start = centers[i],
                end = centers[i + 1],
                strokeWidth = 2f
            )
        }

        gears.forEachIndexed { index, (label, teeth) ->
            val r = radiusFor(teeth)
            val gearColor = if (index % 2 == 0) primary else secondary
            drawCircle(color = gearColor, radius = r, center = centers[index], style = Stroke(width = 6f))
            drawCircle(color = gearColor.copy(alpha = 0.15f), radius = r, center = centers[index])

            val textColorArgb = android.graphics.Color.argb(
                255,
                (onSurface.red * 255).toInt(),
                (onSurface.green * 255).toInt(),
                (onSurface.blue * 255).toInt()
            )
            drawContext.canvas.nativeCanvas.apply {
                val paint = Paint().apply {
                    isAntiAlias = true
                    textAlign = Paint.Align.CENTER
                    textSize = min(size.width, size.height) * 0.07f
                    isFakeBoldText = true
                }
                paint.color = textColorArgb
                drawText(
                    "$label: $teeth",
                    centers[index].x,
                    centers[index].y + r + paint.textSize * 1.3f,
                    paint
                )
            }
        }
    }
}
