package com.robutpit.roachrace.model

import com.robutpit.roachrace.data.SaveState
import kotlin.random.Random

/** Everything that makes levelling take real days instead of one sitting:
 * satiety decays on the wall clock (even while the app is closed), feeding
 * and training are gated by real-time cooldowns, and each session's odds of
 * actually gaining a level shrink as the stat gets higher. Maxing one stat
 * (see [MAX_LEVEL]) at the fastest realistic pace takes about a week; the
 * curve keeps going (slower) past that instead of hard-capping. */
object RoachEconomy {
    const val MAX_LEVEL = 24

    private const val SATIETY_DECAY_PER_HOUR = 100f / 40f // fully drains in ~40h unfed
    private const val DEATH_AFTER_HOURS = 96f // ~4 days completely unfed and it's gone
    const val FEED_COOLDOWN_HOURS = 3f
    const val TRAIN_COOLDOWN_HOURS = 5f
    private const val FEED_SATIETY_GAIN = 30f
    private const val TRAIN_SATIETY_COST = 22f
    private const val TRAIN_MIN_SATIETY = 20f

    private fun hoursSince(millis: Long, now: Long) = (now - millis).coerceAtLeast(0) / 3_600_000f

    fun currentSatiety(save: SaveState, now: Long = System.currentTimeMillis(), trait: Trait? = null): Int {
        val decayMult = trait?.satietyDecayMult ?: 1f
        val decayed = save.satietyBaseline - SATIETY_DECAY_PER_HOUR * decayMult * hoursSince(save.satietyBaselineAtMillis, now)
        return decayed.coerceIn(0f, 100f).toInt()
    }

    fun isDead(save: SaveState, now: Long = System.currentTimeMillis()): Boolean =
        save.breed != null && hoursSince(save.lastFedAtMillis, now) >= DEATH_AFTER_HOURS

    fun feedCooldownRemainingMs(save: SaveState, now: Long = System.currentTimeMillis()): Long =
        (save.lastFedAtMillis + (FEED_COOLDOWN_HOURS * 3_600_000).toLong() - now).coerceAtLeast(0)

    fun trainCooldownRemainingMs(save: SaveState, now: Long = System.currentTimeMillis()): Long =
        (save.lastTrainedAtMillis + (TRAIN_COOLDOWN_HOURS * 3_600_000).toLong() - now).coerceAtLeast(0)

    fun canTrain(save: SaveState, now: Long = System.currentTimeMillis(), trait: Trait? = null): Boolean =
        trainCooldownRemainingMs(save, now) <= 0 && currentSatiety(save, now, trait) >= TRAIN_MIN_SATIETY

    /** Applies a feed: bumps satiety (baseline reset to "now"), resets the
     * starvation clock. Stamina has a chance to tick up too, scaled by the
     * roach's own [Trait]. */
    fun applyFeed(save: SaveState, trait: Trait?, now: Long = System.currentTimeMillis()): SaveState {
        val gain = FEED_SATIETY_GAIN * (trait?.feedGainMult ?: 1f)
        val newSatiety = (currentSatiety(save, now, trait) + gain).coerceIn(0f, 100f)
        val newStamina = if (save.levels.stamina < MAX_LEVEL && Random.nextFloat() < chanceForLevel(save.levels.stamina) * 0.8f) {
            save.levels.stamina + 1
        } else save.levels.stamina
        return save.copy(
            satietyBaseline = newSatiety.toInt(),
            satietyBaselineAtMillis = now,
            lastFedAtMillis = now,
            levels = save.levels.copy(stamina = newStamina),
        )
    }

    /** Applies a training session: costs satiety, chance to tick speed (and
     * a smaller chance for stress resistance), scaled by [Trait]. */
    fun applyTrain(save: SaveState, trait: Trait?, now: Long = System.currentTimeMillis()): SaveState {
        val satietyNow = currentSatiety(save, now, trait)
        val newSatiety = (satietyNow - TRAIN_SATIETY_COST).coerceIn(0f, 100f)
        val chanceMult = trait?.trainChanceMult ?: 1f
        val newSpeed = if (save.levels.speed < MAX_LEVEL && Random.nextFloat() < chanceForLevel(save.levels.speed) * chanceMult) {
            save.levels.speed + 1
        } else save.levels.speed
        val stressMult = trait?.stressGrowthMult ?: 1f
        val newStress = if (save.levels.stress < MAX_LEVEL && Random.nextFloat() < chanceForLevel(save.levels.stress) * 0.5f * stressMult) {
            save.levels.stress + 1
        } else save.levels.stress
        return save.copy(
            satietyBaseline = newSatiety.toInt(),
            satietyBaselineAtMillis = now,
            lastTrainedAtMillis = now,
            levels = save.levels.copy(speed = newSpeed, stress = newStress),
        )
    }

    /** Diminishing returns: easy early gains, real grinding near the cap —
     * this (plus the cooldowns) is what stretches a stat to ~24 over a week
     * of realistic play instead of maxing in one sitting. */
    private fun chanceForLevel(level: Int): Float = (0.85f - level * 0.03f).coerceIn(0.08f, 0.85f)
}
