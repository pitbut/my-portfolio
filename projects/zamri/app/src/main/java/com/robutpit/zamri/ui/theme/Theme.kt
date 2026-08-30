package com.robutpit.zamri.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

val DollRed = Color(0xFFE53935)
val DollGreen = Color(0xFF43A047)
val DollBackground = Color(0xFF101418)
val DollSurface = Color(0xFF1B2127)
val DollAccent = Color(0xFFFFC107)

private val ZamriDarkColors = darkColorScheme(
    primary = DollAccent,
    secondary = DollGreen,
    tertiary = DollRed,
    background = DollBackground,
    surface = DollSurface,
    onBackground = Color.White,
    onSurface = Color.White
)

private val ZamriLightColors = lightColorScheme(
    primary = DollAccent,
    secondary = DollGreen,
    tertiary = DollRed
)

@Composable
fun ZamriTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit
) {
    val colors = if (darkTheme) ZamriDarkColors else ZamriLightColors
    MaterialTheme(colorScheme = colors, content = content)
}
