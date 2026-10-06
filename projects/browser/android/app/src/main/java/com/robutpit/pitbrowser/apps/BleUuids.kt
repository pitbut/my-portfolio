package com.robutpit.pitbrowser.apps

import java.util.UUID

/**
 * UUID сервисов и характеристик Bluetooth: полные ("6e400001-…"), короткие ("180f", "0x2a19")
 * и понятные имена ("battery_service"), как в Web Bluetooth.
 */
object BleUuids {
    private const val BASE_SUFFIX = "-0000-1000-8000-00805f9b34fb"

    private val NAMES = mapOf(
        // сервисы
        "generic_access" to "1800", "generic_attribute" to "1801", "device_information" to "180a",
        "heart_rate" to "180d", "battery_service" to "180f", "human_interface_device" to "1812",
        "cycling_speed_and_cadence" to "1816", "environmental_sensing" to "181a", "running_speed_and_cadence" to "1814",
        // характеристики
        "device_name" to "2a00", "battery_level" to "2a19", "heart_rate_measurement" to "2a37",
        "manufacturer_name_string" to "2a29", "model_number_string" to "2a24", "firmware_revision_string" to "2a26",
        "temperature" to "2a6e", "humidity" to "2a6f",
        // Nordic UART — «последовательный порт» поверх BLE (ESP32, nRF и т.п.)
        "nordic_uart" to "6e400001-b5a3-f393-e0a9-e50e24dcca9e",
        "nordic_uart_rx" to "6e400002-b5a3-f393-e0a9-e50e24dcca9e",
        "nordic_uart_tx" to "6e400003-b5a3-f393-e0a9-e50e24dcca9e",
    )

    /** Классический Bluetooth: последовательный порт (SPP) — HC-05, HC-06, ESP32 BluetoothSerial. */
    val SPP: UUID = UUID.fromString("00001101-0000-1000-8000-00805f9b34fb")

    /** Дескриптор включения уведомлений. */
    val CCCD: UUID = UUID.fromString("00002902-0000-1000-8000-00805f9b34fb")

    private val SHORT = Regex("^(0x)?([0-9a-f]{4}|[0-9a-f]{8})$")
    private val FULL = Regex("^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")

    /** @throws IllegalArgumentException если строка — не UUID */
    fun parse(value: String): UUID {
        val s = value.trim().lowercase()
        NAMES[s]?.let { return parse(it) }
        if (FULL.matches(s)) return UUID.fromString(s)
        SHORT.matchEntire(s)?.let { m ->
            val hex = m.groupValues[2].padStart(8, '0')
            return UUID.fromString(hex + BASE_SUFFIX)
        }
        throw IllegalArgumentException("неверный UUID Bluetooth: «$value»")
    }

    /** Короткая запись для стандартных UUID ("180f"), полная — для остальных. */
    fun format(uuid: UUID): String {
        val s = uuid.toString()
        return if (s.endsWith(BASE_SUFFIX) && s.startsWith("0000")) s.substring(4, 8) else s
    }

    // Байты передаются между JS и браузером в base64 — компактно и без потерь.
    // (java.util.Base64 появился только в Android 8, а мы поддерживаем Android 7.)
    private const val ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
    private val INDEX = IntArray(128) { -1 }.also { t -> ALPHABET.forEachIndexed { i, c -> t[c.code] = i } }

    fun encode(bytes: ByteArray): String {
        val sb = StringBuilder((bytes.size + 2) / 3 * 4)
        var i = 0
        while (i < bytes.size) {
            val b0 = bytes[i].toInt() and 0xff
            val b1 = if (i + 1 < bytes.size) bytes[i + 1].toInt() and 0xff else 0
            val b2 = if (i + 2 < bytes.size) bytes[i + 2].toInt() and 0xff else 0
            sb.append(ALPHABET[b0 shr 2]).append(ALPHABET[(b0 and 3 shl 4) or (b1 shr 4)])
            sb.append(if (i + 1 < bytes.size) ALPHABET[(b1 and 0xf shl 2) or (b2 shr 6)] else '=')
            sb.append(if (i + 2 < bytes.size) ALPHABET[b2 and 0x3f] else '=')
            i += 3
        }
        return sb.toString()
    }

    fun decode(b64: String): ByteArray {
        val s = b64.trim().trimEnd('=')
        if (s.length % 4 == 1) throw IllegalArgumentException("данные должны быть в base64")
        val out = java.io.ByteArrayOutputStream(s.length * 3 / 4)
        var buf = 0
        var bits = 0
        for (c in s) {
            val v = if (c.code < 128) INDEX[c.code] else -1
            if (v < 0) throw IllegalArgumentException("данные должны быть в base64")
            buf = (buf shl 6) or v
            bits += 6
            if (bits >= 8) { bits -= 8; out.write(buf shr bits and 0xff) }
        }
        return out.toByteArray()
    }
}
