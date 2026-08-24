package com.dividinghead.calculator.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp
import com.dividinghead.calculator.data.datastore.ThemeMode

private val Amber = Color(0xFFFFB703)
private val DeepBlue = Color(0xFF1A233C)
private val DeepBlueLight = Color(0xFF2C3A5E)

private val LightColors = lightColorScheme(
    primary = DeepBlue,
    onPrimary = Color.White,
    secondary = Amber,
    onSecondary = Color.Black,
    tertiary = DeepBlueLight
)

private val DarkColors = darkColorScheme(
    primary = Amber,
    onPrimary = Color.Black,
    secondary = DeepBlueLight,
    onSecondary = Color.White,
    tertiary = DeepBlue
)

private fun typography(scale: Float): Typography {
    val base = Typography()
    fun TextStyle.scaled() = copy(fontSize = fontSize * scale, lineHeight = lineHeight * scale)
    return base.copy(
        displayLarge = base.displayLarge.scaled(),
        displayMedium = base.displayMedium.scaled(),
        displaySmall = base.displaySmall.scaled(),
        headlineLarge = base.headlineLarge.scaled(),
        headlineMedium = base.headlineMedium.scaled(),
        headlineSmall = base.headlineSmall.scaled(),
        titleLarge = base.titleLarge.scaled().copy(fontWeight = FontWeight.Bold),
        titleMedium = base.titleMedium.scaled(),
        titleSmall = base.titleSmall.scaled(),
        bodyLarge = base.bodyLarge.scaled(),
        bodyMedium = base.bodyMedium.scaled(),
        bodySmall = base.bodySmall.scaled(),
        labelLarge = base.labelLarge.scaled(),
        labelMedium = base.labelMedium.scaled(),
        labelSmall = base.labelSmall.scaled()
    )
}

/** Regular typography for normal use. */
private val NormalTypography = typography(1.0f)

/** Enlarged typography for the "увеличенный шрифт для цеха" (shop-floor) mode. */
private val ShopFloorTypography = typography(1.35f)

@Composable
fun DividingHeadTheme(
    themeMode: ThemeMode,
    largeFontForShop: Boolean,
    content: @Composable () -> Unit
) {
    val darkTheme = when (themeMode) {
        ThemeMode.SYSTEM -> isSystemInDarkTheme()
        ThemeMode.LIGHT -> false
        ThemeMode.DARK -> true
    }
    val colors = if (darkTheme) DarkColors else LightColors
    val typography = if (largeFontForShop) ShopFloorTypography else NormalTypography

    MaterialTheme(
        colorScheme = colors,
        typography = typography,
        content = content
    )
}
