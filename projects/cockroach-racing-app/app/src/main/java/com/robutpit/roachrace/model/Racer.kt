package com.robutpit.roachrace.model

import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import kotlin.random.Random

data class Levels(val speed: Int = 0, val stamina: Int = 0, val stress: Int = 0)

fun levelBonus(level: Int): Float = 1f + level * 0.05f

class Racer(
    val name: String,
    val isPlayer: Boolean,
    val isRemote: Boolean,
    val breed: Breed,
    val colorLong: Long,
    val levels: Levels,
) {
    val speedBase = breed.baseSpeed * levelBonus(levels.speed)
    val fatigueBase = breed.baseStamina * levelBonus(levels.stamina)
    val stressBase = breed.baseStress * levelBonus(levels.stress)
    val sizeDp = breed.sizeDp

    var progress = mutableFloatStateOf(0f)
    var wobbleCur = mutableFloatStateOf(0f)
    var wobbleTarget = 0f
    var wobbleTimer = 0f
    var spookTimer = mutableFloatStateOf(0f)
    var legPhase = Random.nextFloat() * 10f
    var finished = mutableStateOf(false)
    var finishTimeSec: Float? = null
    var finishOrder: Int? = null
}
