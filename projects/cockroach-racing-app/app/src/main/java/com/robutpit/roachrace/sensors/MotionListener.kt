package com.robutpit.roachrace.sensors

import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import kotlin.math.abs
import kotlin.math.sqrt

/**
 * Watches the accelerometer for a sharp jolt (someone tapping/banging the
 * table the phone sits on) and reports peaks no more often than
 * [cooldownMs]. Uses an adaptive baseline (like [MicListener]'s ambient
 * noise floor) instead of one fixed delta threshold, since a tap felt
 * through a table is much fainter than shaking the phone directly and a
 * single magic number can't cover both. No runtime permission needed on
 * Android for the accelerometer, unlike iOS's devicemotion prompt.
 */
class MotionListener(
    context: Context,
    private val onLevel: (Float) -> Unit,
    private val onPeak: () -> Unit,
) : SensorEventListener {
    private val sensorManager = context.getSystemService(Context.SENSOR_SERVICE) as SensorManager
    private val accelerometer: Sensor? = sensorManager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER)
    private var lastMagnitude: Float? = null
    private var lastPeakAt = 0L
    private var ambient = 0.3f
    private val cooldownMs = 900L

    fun hasSensor(): Boolean = accelerometer != null

    fun start(): Boolean {
        val sensor = accelerometer ?: return false
        lastMagnitude = null
        ambient = 0.3f
        return sensorManager.registerListener(this, sensor, SensorManager.SENSOR_DELAY_GAME)
    }

    fun stop() {
        sensorManager.unregisterListener(this)
        lastMagnitude = null
    }

    override fun onSensorChanged(event: SensorEvent) {
        val mag = sqrt(event.values[0] * event.values[0] + event.values[1] * event.values[1] + event.values[2] * event.values[2])
        val prev = lastMagnitude
        if (prev != null) {
            val delta = abs(mag - prev)
            onLevel((delta / 8f).coerceIn(0f, 1f))
            val now = System.currentTimeMillis()
            val isPeak = delta > ambient * 3f + 0.7f
            if (isPeak && now - lastPeakAt > cooldownMs) {
                lastPeakAt = now
                onPeak()
            }
            if (!isPeak) {
                ambient = ambient * 0.95f + delta * 0.05f
            }
        }
        lastMagnitude = mag
    }

    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) = Unit
}
