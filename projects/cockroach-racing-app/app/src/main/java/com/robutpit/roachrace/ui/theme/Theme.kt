package com.robutpit.roachrace.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

val BgDeep = Color(0xFF14120F)
val BgCard = Color(0xFF2B261E)
val BgCardHi = Color(0xFF332D23)
val BgFaint = Color(0xFF26221B)
val Amber = Color(0xFFE0A458)
val AmberDark = Color(0xFFA97A3C)
val Green = Color(0xFF7C9473)
val Red = Color(0xFFC25B4A)
val TextMain = Color(0xFFF1EAD9)
val TextDim = Color(0xFFB3A892)
val LineColor = Color(0xFF3D362A)

private val scheme = darkColorScheme(
    primary = Amber,
    onPrimary = Color(0xFF241A0C),
    secondary = Green,
    background = BgDeep,
    onBackground = TextMain,
    surface = BgCard,
    onSurface = TextMain,
)

@Composable
fun RoachRaceTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = scheme, content = content)
}
