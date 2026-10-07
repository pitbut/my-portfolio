package com.robutpit.pitbrowser.apps

import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.os.Build
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager

/**
 * Датчики телефона и вибрация для PitSDK.
 * Значения — в системе координат телефона (как в Android): x — вправо, y — вверх по экрану, z — из экрана.
 */
class DeviceSensors(
    context: Context,
    private val onEvent: (type: String, values: FloatArray, timestampNs: Long) -> Unit,
) {
    private val sm = context.getSystemService(Context.SENSOR_SERVICE) as SensorManager
    private val vibrator: Vibrator? = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
        (context.getSystemService(Context.VIBRATOR_MANAGER_SERVICE) as? VibratorManager)?.defaultVibrator
    } else {
        @Suppress("DEPRECATION") context.getSystemService(Context.VIBRATOR_SERVICE) as? Vibrator
    }

    private class Active(val type: String, val sensor: Sensor, val periodUs: Int, val listener: SensorEventListener)

    private val active = mutableMapOf<String, Active>()
    private var paused = false

    /** Датчики, которые есть именно на этом телефоне. */
    fun available(): List<String> = TYPES.filter { (_, t) -> sm.getDefaultSensor(t) != null }.keys.toList()

    fun start(type: String, hz: Int): Boolean {
        val androidType = TYPES[type] ?: return false
        val sensor = sm.getDefaultSensor(androidType) ?: return false
        stop(type)
        val periodUs = 1_000_000 / hz.coerceIn(1, 100)
        val rotation = FloatArray(9)
        val angles = FloatArray(3)
        var last = 0L
        val listener = object : SensorEventListener {
            override fun onSensorChanged(e: SensorEvent) {
                // датчик может присылать чаще, чем просили, — прореживаем
                if (e.timestamp - last < periodUs * 900L) return
                last = e.timestamp
                if (type == "orientation") {
                    // азимут (компас), наклон вперёд-назад и вбок — в градусах
                    SensorManager.getRotationMatrixFromVector(rotation, e.values)
                    SensorManager.getOrientation(rotation, angles)
                    onEvent(type, floatArrayOf(deg(angles[0]), deg(angles[1]), deg(angles[2])), e.timestamp)
                } else {
                    onEvent(type, e.values.copyOf(VALUE_COUNT[type] ?: e.values.size), e.timestamp)
                }
            }
            override fun onAccuracyChanged(s: Sensor?, accuracy: Int) {}
        }
        val a = Active(type, sensor, periodUs, listener)
        active[type] = a
        if (!paused) sm.registerListener(listener, sensor, periodUs)
        return true
    }

    fun stop(type: String) {
        active.remove(type)?.let { sm.unregisterListener(it.listener) }
    }

    fun stopAll() {
        active.values.forEach { sm.unregisterListener(it.listener) }
        active.clear()
        vibrator?.cancel()
    }

    /** Приложение свёрнуто — датчики не тратят батарею. */
    fun pause() {
        paused = true
        active.values.forEach { sm.unregisterListener(it.listener) }
        vibrator?.cancel()
    }

    fun resume() {
        if (!paused) return
        paused = false
        active.values.forEach { sm.registerListener(it.listener, it.sensor, it.periodUs) }
    }

    fun vibrate(pattern: LongArray) {
        val v = vibrator ?: return
        if (!v.hasVibrator() || pattern.isEmpty() || pattern.all { it == 0L }) return v.cancel()
        // узор PitSDK: [вибрация, пауза, вибрация, ...]; у Android первым идёт пауза
        val timings = longArrayOf(0) + pattern
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) v.vibrate(VibrationEffect.createWaveform(timings, -1))
        else @Suppress("DEPRECATION") v.vibrate(timings, -1)
    }

    private fun deg(rad: Float) = Math.toDegrees(rad.toDouble()).toFloat()

    companion object {
        val TYPES = linkedMapOf(
            "accelerometer" to Sensor.TYPE_ACCELEROMETER,
            "gyroscope" to Sensor.TYPE_GYROSCOPE,
            "magnetometer" to Sensor.TYPE_MAGNETIC_FIELD,
            "gravity" to Sensor.TYPE_GRAVITY,
            "linear_acceleration" to Sensor.TYPE_LINEAR_ACCELERATION,
            "rotation_vector" to Sensor.TYPE_ROTATION_VECTOR,
            "orientation" to Sensor.TYPE_ROTATION_VECTOR,
            "light" to Sensor.TYPE_LIGHT,
            "proximity" to Sensor.TYPE_PROXIMITY,
            "pressure" to Sensor.TYPE_PRESSURE,
        )
        private val VALUE_COUNT = mapOf(
            "accelerometer" to 3, "gyroscope" to 3, "magnetometer" to 3, "gravity" to 3,
            "linear_acceleration" to 3, "rotation_vector" to 4, "light" to 1, "proximity" to 1, "pressure" to 1,
        )
    }
}
