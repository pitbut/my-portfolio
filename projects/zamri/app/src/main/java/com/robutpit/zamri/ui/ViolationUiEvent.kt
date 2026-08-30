package com.robutpit.zamri.ui

import android.graphics.Bitmap
import com.robutpit.zamri.motion.SectorLabel

/** Drives the 2-3 second on-screen overlay shown right after a violation is caught. */
data class ViolationUiEvent(
    val label: SectorLabel,
    val markedPhoto: Bitmap
)
