package com.robutpit.roachrace.sensors

import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import kotlin.math.sqrt

/**
 * Watches the accelerometer for a sharp jolt (someone tapping/banging the
 * table the phone sits on) and reports peaks above [threshold], no more
 * often than [cooldownMs]. No runtime permission needed on Android for the
 * accelerometer, unlike iOS's devicemotion prompt.
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
    private val threshold = 6f
    private val cooldownMs = 1200L

    fun hasSensor(): Boolean = accelerometer != null

    fun start(): Boolean {
        val sensor = accelerometer ?: return false
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
            val delta = kotlin.math.abs(mag - prev)
            onLevel(delta)
            val now = System.currentTimeMillis()
            if (delta > threshold && now - lastPeakAt > cooldownMs) {
                lastPeakAt = now
                onPeak()
            }
        }
        lastMagnitude = mag
    }

    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) = Unit
}
