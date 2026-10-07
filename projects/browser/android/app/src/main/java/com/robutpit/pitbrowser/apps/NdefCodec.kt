package com.robutpit.pitbrowser.apps

import org.json.JSONArray
import org.json.JSONObject
import java.io.ByteArrayOutputStream

/**
 * NDEF — формат данных на NFC-метках. Свой кодек (а не android.nfc.NdefRecord), чтобы логику
 * можно было проверить тестами без телефона; на Android байты передаются в NdefMessage как есть.
 *
 * Запись для PitSDK (JSON):
 *   { type: 'text', text, lang }        — текст (RTD Text)
 *   { type: 'url', url }                — ссылка (RTD URI)
 *   { type: 'mime', mime, data }        — свои данные, data в base64 (например, application/json)
 *   { type: 'unknown', tnf, recordType, data } — всё остальное (только чтение)
 */
object NdefCodec {
    private const val TNF_WELL_KNOWN = 1
    private const val TNF_MIME = 2
    private const val TNF_ABSOLUTE_URI = 3
    private const val TNF_EXTERNAL = 4

    private val RTD_TEXT = byteArrayOf('T'.code.toByte())
    private val RTD_URI = byteArrayOf('U'.code.toByte())

    /** Сокращения начала ссылки из стандарта NFC Forum (код = индекс). */
    private val URI_PREFIXES = listOf(
        "", "http://www.", "https://www.", "http://", "https://", "tel:", "mailto:",
        "ftp://anonymous:anonymous@", "ftp://ftp.", "ftps://", "sftp://", "smb://", "nfs://", "ftp://",
        "dav://", "news:", "telnet://", "imap:", "rtsp://", "urn:", "pop:", "sip:", "sips:", "tftp:",
        "btspp://", "btl2cap://", "btgoep://", "tcpobex://", "irdaobex://", "file://", "urn:epc:id:",
        "urn:epc:tag:", "urn:epc:pat:", "urn:epc:raw:", "urn:epc:", "urn:nfc:",
    )

    class NdefException(message: String) : Exception(message)

    // ------------------------------------------------------------------ чтение

    fun decode(message: ByteArray): JSONArray {
        val out = JSONArray()
        var i = 0
        fun need(n: Int) { if (i + n > message.size) throw NdefException("повреждённые данные на метке") }
        while (i < message.size) {
            need(2)
            val header = message[i].toInt() and 0xff
            val tnf = header and 0x07
            val shortRecord = header and 0x10 != 0
            val hasId = header and 0x08 != 0
            val typeLen = message[i + 1].toInt() and 0xff
            i += 2
            val payloadLen: Int
            if (shortRecord) { need(1); payloadLen = message[i].toInt() and 0xff; i += 1 }
            else {
                need(4)
                val len = ((message[i].toLong() and 0xff) shl 24) or ((message[i + 1].toLong() and 0xff) shl 16) or
                    ((message[i + 2].toLong() and 0xff) shl 8) or (message[i + 3].toLong() and 0xff)
                if (len > message.size) throw NdefException("повреждённые данные на метке")
                payloadLen = len.toInt(); i += 4
            }
            val idLen = if (hasId) { need(1); (message[i].toInt() and 0xff).also { i += 1 } } else 0
            need(typeLen + idLen + payloadLen)
            val type = message.copyOfRange(i, i + typeLen); i += typeLen
            i += idLen
            val payload = message.copyOfRange(i, i + payloadLen); i += payloadLen
            out.put(record(tnf, type, payload))
            if (header and 0x40 != 0) break // ME — последняя запись
        }
        return out
    }

    private fun record(tnf: Int, type: ByteArray, payload: ByteArray): JSONObject = when {
        tnf == TNF_WELL_KNOWN && type.contentEquals(RTD_TEXT) && payload.isNotEmpty() -> {
            val status = payload[0].toInt() and 0xff
            val langLen = (status and 0x3f).coerceAtMost(payload.size - 1)
            val charset = if (status and 0x80 != 0) Charsets.UTF_16 else Charsets.UTF_8
            JSONObject().put("type", "text")
                .put("lang", String(payload, 1, langLen, Charsets.US_ASCII))
                .put("text", String(payload, 1 + langLen, payload.size - 1 - langLen, charset))
        }
        tnf == TNF_WELL_KNOWN && type.contentEquals(RTD_URI) && payload.isNotEmpty() -> {
            val prefix = URI_PREFIXES.getOrElse(payload[0].toInt() and 0xff) { "" }
            JSONObject().put("type", "url").put("url", prefix + String(payload, 1, payload.size - 1, Charsets.UTF_8))
        }
        tnf == TNF_ABSOLUTE_URI -> JSONObject().put("type", "url").put("url", String(type, Charsets.UTF_8))
        tnf == TNF_MIME -> JSONObject().put("type", "mime").put("mime", String(type, Charsets.US_ASCII)).put("data", BleUuids.encode(payload))
        else -> JSONObject().put("type", "unknown").put("tnf", tnf)
            .put("recordType", String(type, Charsets.UTF_8)).put("data", BleUuids.encode(payload))
    }

    // ------------------------------------------------------------------ запись

    fun encode(records: JSONArray): ByteArray {
        if (records.length() == 0) throw NdefException("нечего записывать")
        val out = ByteArrayOutputStream()
        for (n in 0 until records.length()) {
            val r = records.optJSONObject(n) ?: throw NdefException("запись №${n + 1} должна быть объектом")
            val (tnf, type, payload) = when (r.optString("type")) {
                "text" -> {
                    val lang = r.optString("lang", "ru").ifEmpty { "ru" }.toByteArray(Charsets.US_ASCII)
                    if (lang.size > 63) throw NdefException("слишком длинный код языка")
                    Triple(TNF_WELL_KNOWN, RTD_TEXT, byteArrayOf(lang.size.toByte()) + lang + r.optString("text").toByteArray(Charsets.UTF_8))
                }
                "url" -> {
                    val url = r.optString("url").ifEmpty { throw NdefException("пустая ссылка") }
                    // самый длинный подходящий префикс — экономит место на метке
                    val code = URI_PREFIXES.indices.drop(1).filter { url.startsWith(URI_PREFIXES[it]) }.maxByOrNull { URI_PREFIXES[it].length } ?: 0
                    Triple(TNF_WELL_KNOWN, RTD_URI, byteArrayOf(code.toByte()) + url.substring(URI_PREFIXES[code].length).toByteArray(Charsets.UTF_8))
                }
                "mime" -> {
                    val mime = r.optString("mime").ifEmpty { throw NdefException("не указан mime") }
                    Triple(TNF_MIME, mime.toByteArray(Charsets.US_ASCII), BleUuids.decode(r.optString("data")))
                }
                else -> throw NdefException("неизвестный тип записи «${r.optString("type")}» (text, url, mime)")
            }
            var header = tnf
            if (n == 0) header = header or 0x80 // MB — первая
            if (n == records.length() - 1) header = header or 0x40 // ME — последняя
            val short = payload.size < 256
            if (short) header = header or 0x10
            out.write(header)
            out.write(type.size)
            if (short) out.write(payload.size)
            else { out.write(payload.size ushr 24); out.write(payload.size ushr 16 and 0xff); out.write(payload.size ushr 8 and 0xff); out.write(payload.size and 0xff) }
            out.write(type)
            out.write(payload)
        }
        return out.toByteArray()
    }

    /** UID метки в привычном виде: 04:A2:3B:… */
    fun formatId(id: ByteArray) = id.joinToString(":") { "%02X".format(it.toInt() and 0xff) }
}
