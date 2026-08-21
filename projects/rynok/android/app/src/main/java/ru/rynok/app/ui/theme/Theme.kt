package ru.rynok.app.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

val RynokGreen = Color(0xFF2E7D32)
val RynokGreenDark = Color(0xFF1B5E20)
val RynokAmber = Color(0xFFF9A825)
val RynokRed = Color(0xFFC62828)
val RynokBackground = Color(0xFFF7F7F2)
val RynokSurface = Color(0xFFFFFFFF)

private val LightColors = lightColorScheme(
    primary = RynokGreen,
    onPrimary = Color.White,
    secondary = RynokAmber,
    background = RynokBackground,
    surface = RynokSurface,
    error = RynokRed,
)

private val DarkColors = darkColorScheme(
    primary = RynokGreen,
    onPrimary = Color.White,
    secondary = RynokAmber,
    error = RynokRed,
)

@Composable
fun RynokTheme(content: @Composable () -> Unit) {
    val colors = if (isSystemInDarkTheme()) DarkColors else LightColors
    MaterialTheme(colorScheme = colors, content = content)
}
