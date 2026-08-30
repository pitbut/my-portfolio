package com.robutpit.roachrace.engine

import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import com.robutpit.roachrace.model.Racer
import com.robutpit.roachrace.model.Track
import kotlin.math.abs
import kotlin.math.pow
import kotlin.random.Random

private fun clamp(v: Float, a: Float, b: Float) = v.coerceIn(a, b)
private fun lerp(a: Float, b: Float, t: Float) = a + (b - a) * t

/**
 * Same tuning constants as the browser prototype (projects/cockroach-racing),
 * kept in sync so both versions feel the same to play.
 */
class RaceEngine(
    val track: Track,
    val racers: List<Racer>,
    private val onSpook: ((sourceLabel: String, targetName: String) -> Unit)? = null,
) {
    var running = mutableStateOf(false)
    var done = mutableStateOf(false)
    var elapsed = 0f
        private set
    private var finishedCount = 0
    val log = mutableStateListOf<String>()

    var hardcore = false

    private val pxPerSec = 130f

    fun start() {
        running.value = true
    }

    /** Always leaves a visible trace in [log] — even when there is nobody left
     * to spook — so a mic/motion trigger is never silent: the player gets
     * proof the sensor actually fired, whether or not it had an effect. */
    fun spookRandomRacer(sourceLabel: String, targetIdOverride: Int? = null) {
        val pool = racers.filter { !it.finished.value && (hardcore || !it.isPlayer) }
        if (pool.isEmpty()) {
            log.add("$sourceLabel: сигнал услышан, но пугать уже некого — все финишировали")
            return
        }
        val target = if (targetIdOverride != null && targetIdOverride < racers.size) {
            racers[targetIdOverride]
        } else {
            pool[Random.nextInt(pool.size)]
        }
        val baseDur = 1.1f
        target.spookTimer.value = maxOf(target.spookTimer.value, baseDur / target.stressBase)
        target.wobbleTarget = if (Random.nextBoolean()) -1f else 1f
        // Nudge the visible wobble immediately instead of waiting for the next
        // step() tick, so the reaction is visible even before the race starts.
        target.wobbleCur.value = lerp(target.wobbleCur.value, target.wobbleTarget, 0.6f)
        val runningNote = if (!running.value) " (нажми «Старт», чтобы это было видно в забеге)" else ""
        val msg = "$sourceLabel → «${target.name}» испугался и сбился с курса!$runningNote"
        log.add(msg)
        onSpook?.invoke(sourceLabel, target.name)
    }

    private fun updateWobble(r: Racer, dt: Float, frictionMult: Float) {
        r.wobbleTimer -= dt
        if (r.wobbleTimer <= 0f) {
            r.wobbleTimer = 0.25f + Random.nextFloat() * 0.4f
            val trained = (r.levels.speed + r.levels.stamina + r.levels.stress) / 30f
            val amp = clamp(0.9f - trained * 0.55f, 0.15f, 0.95f) * frictionMult
            r.wobbleTarget = (Random.nextFloat() * 2f - 1f) * amp
        }
        val t = 1f - 0.001f.toDouble().pow(dt.toDouble()).toFloat()
        r.wobbleCur.value = lerp(r.wobbleCur.value, r.wobbleTarget, t)
    }

    /** Advances local simulation by dt seconds. Racers marked isRemote are skipped
     * (their state instead arrives from the Bluetooth link — see BtRaceLink). */
    fun step(dt: Float) {
        if (!running.value) return
        elapsed += dt

        for (r in racers) {
            if (r.finished.value || r.isRemote) continue
            r.spookTimer.value = maxOf(0f, r.spookTimer.value - dt)
            r.legPhase += dt * 8f

            var obstacleMult = 1f
            for (o in track.obstacles) {
                val opos = o.pos * track.distance
                if (abs(r.progress.floatValue - opos) < track.distance * 0.03f) {
                    obstacleMult = minOf(obstacleMult, o.slow)
                }
            }

            updateWobble(r, dt, track.friction * (if (r.spookTimer.value > 0f) 1.8f else 1f))

            val control = 1f - abs(r.wobbleCur.value) * 0.55f
            val spookMult = if (r.spookTimer.value > 0f) 0.45f else 1f
            val raceFrac = clamp(r.progress.floatValue / track.distance, 0f, 1f)
            val fatigueMult = clamp(1f - raceFrac * (0.4f / r.fatigueBase), 0.5f, 1f)

            val velocity = pxPerSec * r.speedBase * fatigueMult * obstacleMult * control * spookMult
            r.progress.floatValue += velocity * dt

            if (r.progress.floatValue >= track.distance) {
                r.progress.floatValue = track.distance
                r.finished.value = true
                r.finishTimeSec = elapsed
                r.finishOrder = finishedCount++
            }
        }

        val allDone = racers.all { it.finished.value } || elapsed > 60f
        if (allDone) {
            for (r in racers) {
                if (!r.finished.value) {
                    r.finished.value = true
                    r.finishTimeSec = elapsed
                    r.finishOrder = finishedCount++
                }
            }
            running.value = false
            done.value = true
        }
    }

    /** Applies a progress/wobble snapshot received from the host over Bluetooth
     * onto the local racer object marked isRemote, so both phones render the
     * same shared field. */
    fun applyRemoteSnapshot(index: Int, progress: Float, wobble: Float, spook: Float, finished: Boolean) {
        val r = racers.getOrNull(index) ?: return
        r.progress.floatValue = progress
        r.wobbleCur.value = wobble
        r.spookTimer.value = spook
        if (finished && !r.finished.value) {
            r.finished.value = true
            r.finishTimeSec = elapsed
            r.finishOrder = finishedCount++
        }
    }
}
