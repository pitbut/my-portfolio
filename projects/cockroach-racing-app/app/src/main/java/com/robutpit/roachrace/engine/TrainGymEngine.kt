package com.robutpit.roachrace.engine

import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.ui.geometry.Offset
import kotlin.math.hypot
import kotlin.random.Random

enum class GymMode { WANDER, EATING, TRAINING }
enum class GymResult { NONE, FED, TRAINED }

/**
 * Small physics sandbox behind the "gym" training screen: the roach wanders,
 * walks to food and eats it, or runs a timed training lap while dodging
 * obstacles the player drops in with a tap and can be nudged around with a
 * drag. Everything is in a normalised 0..1 arena; the screen multiplies by
 * the actual Canvas size when drawing.
 */
class TrainGymEngine {
    private val posState = mutableStateOf(Offset(0.5f, 0.55f))
    val pos: Offset get() = posState.value
    private var vel = Offset(0f, 0f)
    private var wanderTarget = Offset(0.5f, 0.55f)
    private var wanderTimer = 0f

    var mode = mutableStateOf(GymMode.WANDER)
        private set
    var sessionTimer = mutableFloatStateOf(0f)
        private set
    var sessionDuration = 1f
        private set
    var foodPos: Offset? = null
        private set
    var eatingArrived = mutableStateOf(false)
        private set

    var wobble = mutableFloatStateOf(0f)
        private set
    var legPhase = 0f
        private set
    var lastResult = mutableStateOf(GymResult.NONE)

    /** A careless direct tap on the roach (not the wider push-drag zone)
     * has a chance of squishing it for good — set once and stays set. */
    var squished = mutableStateOf(false)
        private set
    private val directHitRadius = 0.075f
    private val squishChance = 0.3f

    val obstacles = mutableStateListOf<Offset>()
    private val maxObstacles = 6

    private var onFeedComplete: (() -> Unit)? = null
    private var onTrainComplete: (() -> Unit)? = null

    fun setCallbacks(onFeed: () -> Unit, onTrain: () -> Unit) {
        onFeedComplete = onFeed
        onTrainComplete = onTrain
    }

    fun startFeeding() {
        if (mode.value != GymMode.WANDER || squished.value) return
        foodPos = Offset(0.15f + Random.nextFloat() * 0.7f, 0.2f + Random.nextFloat() * 0.6f)
        eatingArrived.value = false
        // A real cockroach spends a good while at a food source, not a
        // couple of seconds — long enough here to actually feel unhurried.
        sessionDuration = 55f + Random.nextFloat() * 20f
        sessionTimer.floatValue = sessionDuration
        mode.value = GymMode.EATING
    }

    fun startTraining() {
        if (mode.value != GymMode.WANDER || squished.value) return
        sessionDuration = 7f
        sessionTimer.floatValue = sessionDuration
        mode.value = GymMode.TRAINING
    }

    /** Tap on empty ground drops/removes an obstacle peg; tapping an existing
     * one removes it, so the player can freely redesign the little obstacle
     * course. A tap that lands *directly* on the roach (tighter than the
     * push-drag zone) is an accidental press — real risk of squishing it,
     * same as bumping a real bug with your finger. */
    fun handleTap(normPos: Offset) {
        if (squished.value) return
        val distToRoach = hypot((normPos.x - pos.x).toDouble(), (normPos.y - pos.y).toDouble())
        if (distToRoach < directHitRadius) {
            if (Random.nextFloat() < squishChance) squished.value = true
            return
        }
        if (distToRoach < 0.12) return
        val hit = obstacles.firstOrNull { hypot((it.x - normPos.x).toDouble(), (it.y - normPos.y).toDouble()) < 0.06 }
        if (hit != null) {
            obstacles.remove(hit)
        } else {
            if (obstacles.size >= maxObstacles) obstacles.removeAt(0)
            obstacles.add(normPos)
        }
    }

    /** Drag near the roach shoves it around — a finger poking it in the gym. */
    fun handlePush(normDelta: Offset) {
        vel = Offset(vel.x + normDelta.x * 2.2f, vel.y + normDelta.y * 2.2f)
    }

    fun isNearRoach(normPos: Offset): Boolean =
        hypot((normPos.x - pos.x).toDouble(), (normPos.y - pos.y).toDouble()) < 0.14

    fun step(dt: Float) {
        if (squished.value) return
        legPhase += dt * (6f + hypot(vel.x.toDouble(), vel.y.toDouble()).toFloat() * 20f)

        when (mode.value) {
            GymMode.WANDER -> stepWander(dt)
            GymMode.EATING -> stepEating(dt)
            GymMode.TRAINING -> stepTraining(dt)
        }

        applyObstacleRepulsion(dt)
        integrate(dt)
        wobble.floatValue = (vel.x * 0.6f).coerceIn(-1f, 1f)
    }

    private fun stepWander(dt: Float) {
        wanderTimer -= dt
        if (wanderTimer <= 0f) {
            wanderTimer = 1.2f + Random.nextFloat() * 1.5f
            wanderTarget = Offset(0.15f + Random.nextFloat() * 0.7f, 0.2f + Random.nextFloat() * 0.6f)
        }
        steerToward(wanderTarget, 0.35f, dt)
    }

    private fun stepEating(dt: Float) {
        val food = foodPos ?: run { mode.value = GymMode.WANDER; return }
        val dist = hypot((food.x - pos.x).toDouble(), (food.y - pos.y).toDouble()).toFloat()
        if (!eatingArrived.value) {
            steerToward(food, 0.55f, dt)
            if (dist < 0.05f) eatingArrived.value = true
        } else {
            vel = Offset(vel.x * 0.8f, vel.y * 0.8f)
        }
        sessionTimer.floatValue -= dt
        if (sessionTimer.floatValue <= 0f) {
            foodPos = null
            mode.value = GymMode.WANDER
            lastResult.value = GymResult.FED
            onFeedComplete?.invoke()
        }
    }

    private var trainLapTimer = 0f
    private var trainTarget = Offset(0.5f, 0.3f)

    private fun stepTraining(dt: Float) {
        trainLapTimer -= dt
        if (trainLapTimer <= 0f) {
            trainLapTimer = 0.7f + Random.nextFloat() * 0.6f
            trainTarget = Offset(0.12f + Random.nextFloat() * 0.76f, 0.15f + Random.nextFloat() * 0.7f)
        }
        steerToward(trainTarget, 0.75f, dt)
        sessionTimer.floatValue -= dt
        if (sessionTimer.floatValue <= 0f) {
            mode.value = GymMode.WANDER
            lastResult.value = GymResult.TRAINED
            onTrainComplete?.invoke()
        }
    }

    private fun steerToward(target: Offset, speed: Float, dt: Float) {
        val dx = target.x - pos.x
        val dy = target.y - pos.y
        val dist = hypot(dx.toDouble(), dy.toDouble()).toFloat()
        if (dist < 0.001f) return
        val nx = dx / dist
        val ny = dy / dist
        vel = Offset(vel.x + nx * speed * dt * 3f, vel.y + ny * speed * dt * 3f)
    }

    private fun applyObstacleRepulsion(dt: Float) {
        for (o in obstacles) {
            val dx = pos.x - o.x
            val dy = pos.y - o.y
            val dist = hypot(dx.toDouble(), dy.toDouble()).toFloat()
            val radius = 0.09f
            if (dist in 0.0001f..radius) {
                val push = (radius - dist) / radius
                vel = Offset(vel.x + (dx / dist) * push * 2.5f * dt * 10f, vel.y + (dy / dist) * push * 2.5f * dt * 10f)
            }
        }
    }

    private fun integrate(dt: Float) {
        vel = Offset(vel.x * 0.90f, vel.y * 0.90f)
        var nx = pos.x + vel.x * dt
        var ny = pos.y + vel.y * dt
        if (nx < 0.06f) { nx = 0.06f; vel = Offset(-vel.x * 0.4f, vel.y) }
        if (nx > 0.94f) { nx = 0.94f; vel = Offset(-vel.x * 0.4f, vel.y) }
        if (ny < 0.08f) { ny = 0.08f; vel = Offset(vel.x, -vel.y * 0.4f) }
        if (ny > 0.92f) { ny = 0.92f; vel = Offset(vel.x, -vel.y * 0.4f) }
        posState.value = Offset(nx, ny)
    }
}
