package com.robutpit.pitbrowser.apps

import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class NdefCodecTest {
    private fun bytes(vararg v: Int) = ByteArray(v.size) { v[it].toByte() }
    private fun recs(vararg r: JSONObject) = JSONArray(r.toList())

    @Test fun encodesTextLikeStandard() {
        // эталон из спецификации NFC Forum: текст "hello", язык "en"
        val expected = bytes(0xD1, 0x01, 0x08, 0x54, 0x02, 0x65, 0x6E) + "hello".toByteArray()
        assertArrayEquals(expected, NdefCodec.encode(recs(JSONObject().put("type", "text").put("text", "hello").put("lang", "en"))))
    }

    @Test fun encodesUrlWithShortestPrefix() {
        val enc = NdefCodec.encode(recs(JSONObject().put("type", "url").put("url", "https://www.example.com")))
        assertArrayEquals(bytes(0xD1, 0x01, 0x0C, 0x55, 0x02) + "example.com".toByteArray(), enc)
        assertEquals("https://www.example.com", NdefCodec.decode(enc).getJSONObject(0).getString("url"))
    }

    @Test fun roundTripSeveralRecordsIncludingLong() {
        val long = "Б".repeat(400) // > 255 байт — длинная запись
        val json = BleUuids.encode("""{"level":3}""".toByteArray())
        val enc = NdefCodec.encode(recs(
            JSONObject().put("type", "text").put("text", "Привет, PitBrowser!"),
            JSONObject().put("type", "url").put("url", "tel:+998901234567"),
            JSONObject().put("type", "mime").put("mime", "application/json").put("data", json),
            JSONObject().put("type", "text").put("text", long),
        ))
        val dec = NdefCodec.decode(enc)
        assertEquals(4, dec.length())
        assertEquals("Привет, PitBrowser!", dec.getJSONObject(0).getString("text"))
        assertEquals("ru", dec.getJSONObject(0).getString("lang"))
        assertEquals("tel:+998901234567", dec.getJSONObject(1).getString("url"))
        assertEquals("application/json", dec.getJSONObject(2).getString("mime"))
        assertEquals(json, dec.getJSONObject(2).getString("data"))
        assertEquals(long, dec.getJSONObject(3).getString("text"))
    }

    @Test fun rejectsBadInputAndCorruptedTags() {
        assertThrows(NdefCodec.NdefException::class.java) { NdefCodec.encode(JSONArray()) }
        assertThrows(NdefCodec.NdefException::class.java) { NdefCodec.encode(recs(JSONObject().put("type", "video"))) }
        assertThrows(NdefCodec.NdefException::class.java) { NdefCodec.encode(recs(JSONObject().put("type", "url").put("url", ""))) }
        // обрезанные данные с метки — понятная ошибка, а не падение
        val enc = NdefCodec.encode(recs(JSONObject().put("type", "text").put("text", "hello")))
        assertThrows(NdefCodec.NdefException::class.java) { NdefCodec.decode(enc.copyOf(enc.size - 3)) }
        assertEquals("04:A2:FF", NdefCodec.formatId(bytes(0x04, 0xA2, 0xFF)))
    }
}
