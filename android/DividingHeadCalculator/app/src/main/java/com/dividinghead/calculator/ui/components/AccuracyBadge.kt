package com.dividinghead.calculator.ui.components

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import kotlin.math.abs

@Composable
fun AccuracyBadge(
    exact: Boolean,
    errorDescription: String?,
    modifier: Modifier = Modifier,
    warningLevel: Boolean = false,
    onShowAlternatives: (() -> Unit)? = null
) {
    val color = when {
        exact -> Color(0xFF2E7D32)
        warningLevel -> Color(0xFFC62828)
        else -> Color(0xFFEF6C00)
    }
    Card(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = color.copy(alpha = 0.15f))
    ) {
        Column(Modifier.padding(12.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(
                    imageVector = if (exact) Icons.Filled.CheckCircle else Icons.Filled.Warning,
                    contentDescription = null,
                    tint = color
                )
                Text(
                    text = if (exact) "Точное деление" else "Приближённое деление",
                    style = MaterialTheme.typography.titleMedium,
                    color = color,
                    modifier = Modifier.padding(start = 8.dp)
                )
            }
            if (!exact && errorDescription != null) {
                Text(
                    text = errorDescription,
                    style = MaterialTheme.typography.bodyMedium,
                    modifier = Modifier.padding(top = 4.dp, start = 32.dp)
                )
            }
            if (!exact && onShowAlternatives != null) {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                    TextButton(onClick = onShowAlternatives) {
                        Text("Показать другие варианты")
                    }
                }
            }
        }
    }
}

fun formatArcError(arcSeconds: Double, percentOfStep: Double): String {
    val absSec = abs(arcSeconds)
    val angleText = if (absSec >= 60) "${"%.1f".format(absSec / 60.0)}′" else "${"%.0f".format(absSec)}″"
    return "Ошибка: $angleText (${"%.2f".format(abs(percentOfStep))}% от шага деления)"
}
