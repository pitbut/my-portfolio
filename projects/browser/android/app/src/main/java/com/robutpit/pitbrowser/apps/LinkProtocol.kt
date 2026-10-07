package com.robutpit.pitbrowser.apps

import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.util.UUID

/**
 * PitLink — игры между телефонами по Bluetooth LE без интернета и без сопряжения.
 *
 * Хост (телефон, создавший комнату) — BLE-периферия с GATT-сервером; игроки подключаются к нему.
 * Сообщение — JSON-конверт; длинные сообщения режутся на пакеты под размер BLE-пакета (MTU):
 *   байт 0 — флаги (FIRST, LAST), дальше — кусок UTF-8 JSON.
 * BLE доставляет пакеты одного соединения по порядку и без потерь, поэтому этого достаточно.
 */
object LinkProtocol {
    /** Характеристика для обмена сообщениями (одна, с записью и уведомлениями). */
    val DATA_CHAR: UUID = UUID.fromString("7a1e0002-9c3f-4d2b-8f6a-50495442524b")

    /** Код производителя 0xFFFF зарезервирован для тестов — в нём передаём название комнаты. */
    const val MANUFACTURER_ID = 0xFFFF
    const val MAX_ROOM_NAME_BYTES = 24
    const val MAX_MESSAGE = 64 * 1024

    private const val FIRST = 1
    private const val LAST = 2

    /** У каждой игры свой UUID сервиса — игроки находят комнаты только своей игры. */
    fun serviceUuid(appId: String): UUID = UUID.nameUUIDFromBytes("pitlink:$appId".toByteArray(Charsets.UTF_8))

    /** Название комнаты, обрезанное по границе символа, чтобы влезть в рекламный пакет BLE. */
    fun roomNameBytes(name: String): ByteArray {
        var s = name.trim().ifEmpty { "Комната" }
        while (s.toByteArray(Charsets.UTF_8).size > MAX_ROOM_NAME_BYTES) s = s.dropLast(1)
        return s.toByteArray(Charsets.UTF_8)
    }

    /** Нарезать сообщение на пакеты; mtu — размер BLE-пакета (полезная нагрузка = mtu − 3). */
    fun split(message: ByteArray, mtu: Int): List<ByteArray> {
        require(message.size <= MAX_MESSAGE) { "сообщение больше ${MAX_MESSAGE / 1024} КБ" }
        val chunk = (mtu - 3 - 1).coerceAtLeast(1)
        if (message.isEmpty()) return listOf(byteArrayOf((FIRST or LAST).toByte()))
        val out = ArrayList<ByteArray>((message.size + chunk - 1) / chunk)
        var i = 0
        while (i < message.size) {
            val end = minOf(message.size, i + chunk)
            var flags = 0
            if (i == 0) flags = flags or FIRST
            if (end == message.size) flags = flags or LAST
            out += byteArrayOf(flags.toByte()) + message.copyOfRange(i, end)
            i = end
        }
        return out
    }

    /** Сборка пакетов одного отправителя обратно в сообщения. */
    class Assembler {
        private var buf: ByteArrayOutputStream? = null

        /** Возвращает целое сообщение, когда пришёл последний пакет, иначе null. */
        fun feed(packet: ByteArray): ByteArray? {
            if (packet.isEmpty()) return null
            val flags = packet[0].toInt()
            if (flags and FIRST != 0) buf = ByteArrayOutputStream()
            val b = buf ?: return null // начало потеряно — ждём следующее сообщение
            b.write(packet, 1, packet.size - 1)
            if (b.size() > MAX_MESSAGE) { buf = null; return null }
            if (flags and LAST != 0) { buf = null; return b.toByteArray() }
            return null
        }
    }

    // ------------------------------------------------------------ конверты

    /** Служебные и игровые сообщения: t = hello | welcome | join | leave | msg */
    fun envelope(type: String, body: JSONObject = JSONObject()): ByteArray = body.put("t", type).toString().toByteArray(Charsets.UTF_8)

    fun parse(bytes: ByteArray): JSONObject? = runCatching { JSONObject(String(bytes, Charsets.UTF_8)) }.getOrNull()?.takeIf { it.has("t") }
}
