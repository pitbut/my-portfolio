package com.dividinghead.calculator.data.db

import androidx.room.Entity
import androidx.room.PrimaryKey

/**
 * A user-defined dividing head preset. Circles are stored as a flat, comma-separated list
 * (unlike the built-in presets, custom ones do not distinguish between separate physical plates).
 */
@Entity(tableName = "presets")
data class PresetEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val name: String,
    val characteristicN: Int,
    val circlesCsv: String,
    val gearsCsv: String,
    val leadScrewPitchMm: Double,
    val isMetric: Boolean
)
