package com.robutpit.zamri.data.db

import androidx.room.Entity
import androidx.room.PrimaryKey

enum class ViolationSide { LEFT, CENTER, RIGHT }

/**
 * One recorded movement violation caught during a red-light phase.
 *
 * [lane] is the 1-based sector index counted left-to-right across the whole
 * frame (matches [settings sectors][com.robutpit.zamri.data.GameSettings.sectorCount]);
 * [sideLane] is the human-friendly number used in the voice callout, counted
 * from the center outwards on the announced [side] (e.g. "Слева, второй").
 */
@Entity(tableName = "violations")
data class ViolationEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val timestampMillis: Long,
    val round: Int,
    val lane: Int,
    val sideLane: Int,
    val side: ViolationSide,
    val photoUri: String,
    val motionScore: Float
)
