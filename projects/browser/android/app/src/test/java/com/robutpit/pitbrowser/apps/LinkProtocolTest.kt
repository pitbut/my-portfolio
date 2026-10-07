package com.robutpit.pitbrowser.apps

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import org.json.JSONObject
import kotlin.random.Random

class LinkProtocolTest {
    @Test fun splitAndAssembleRoundTrip() {
        val r = Random(7)
        for (mtu in listOf(23, 64, 185, 247, 517)) {
            repeat(50) {
                val msg = ByteArray(r.nextInt(0, 5000)).also { r.nextBytes(it) }
                val packets = LinkProtocol.split(msg, mtu)
                assertTrue("пакет влезает в MTU", packets.all { it.size <= mtu - 3 })
                val a = LinkProtocol.Assembler()
                val out = packets.mapNotNull { a.feed(it) }
                assertEquals(1, out.size)
                assertArrayEquals(msg, out[0])
            }
        }
    }

    @Test fun assemblerHandlesConsecutiveMessagesAndLostStart() {
        val a = LinkProtocol.Assembler()
        val m1 = "привет".toByteArray()
        val m2 = ByteArray(300) { it.toByte() }
        val p2 = LinkProtocol.split(m2, 23)
        // хвост сообщения без начала игнорируется
        assertNull(a.feed(p2[1]))
        assertArrayEquals(m1, LinkProtocol.split(m1, 23).mapNotNull { a.feed(it) }.single())
        assertArrayEquals(m2, p2.mapNotNull { a.feed(it) }.single())
    }

    @Test fun envelopes() {
        val bytes = LinkProtocol.envelope("msg", JSONObject().put("from", "p2").put("data", JSONObject().put("x", 1)))
        val m = LinkProtocol.parse(bytes)!!
        assertEquals("msg", m.getString("t"))
        assertEquals(1, m.getJSONObject("data").getInt("x"))
        assertNull(LinkProtocol.parse("не json".toByteArray()))
        assertNull(LinkProtocol.parse("{\"x\":1}".toByteArray()))
    }

    @Test fun roomUuidPerGameAndNameLimit() {
        assertEquals(LinkProtocol.serviceUuid("reaction-duel"), LinkProtocol.serviceUuid("reaction-duel"))
        assertNotEquals(LinkProtocol.serviceUuid("reaction-duel"), LinkProtocol.serviceUuid("tilt-coins"))
        val name = LinkProtocol.roomNameBytes("Очень длинное название комнаты для игры")
        assertTrue(name.size <= LinkProtocol.MAX_ROOM_NAME_BYTES)
        // обрезка не ломает UTF-8
        assertEquals(String(name, Charsets.UTF_8).toByteArray(Charsets.UTF_8).size, name.size)
        assertEquals("Комната", String(LinkProtocol.roomNameBytes("  "), Charsets.UTF_8))
    }
}
