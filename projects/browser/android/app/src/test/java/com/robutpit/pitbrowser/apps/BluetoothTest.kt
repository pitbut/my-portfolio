package com.robutpit.pitbrowser.apps

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder
import java.util.UUID
import kotlin.random.Random

class BluetoothTest {
    @get:Rule val tmp = TemporaryFolder()

    @Test fun parsesUuidForms() {
        val battery = UUID.fromString("0000180f-0000-1000-8000-00805f9b34fb")
        assertEquals(battery, BleUuids.parse("180f"))
        assertEquals(battery, BleUuids.parse("0x180F"))
        assertEquals(battery, BleUuids.parse("battery_service"))
        assertEquals(battery, BleUuids.parse("0000180F-0000-1000-8000-00805F9B34FB"))
        assertEquals(UUID.fromString("6e400001-b5a3-f393-e0a9-e50e24dcca9e"), BleUuids.parse("nordic_uart"))
        listOf("", "xyz", "12345", "battery").forEach { assertThrows(it, IllegalArgumentException::class.java) { BleUuids.parse(it) } }
    }

    @Test fun formatsShortForStandard() {
        assertEquals("2a37", BleUuids.format(BleUuids.parse("heart_rate_measurement")))
        assertEquals("6e400003-b5a3-f393-e0a9-e50e24dcca9e", BleUuids.format(BleUuids.parse("nordic_uart_tx")))
    }

    @Test fun base64MatchesJvm() {
        val r = Random(42)
        repeat(200) {
            val bytes = ByteArray(r.nextInt(0, 600)).also { r.nextBytes(it) }
            val ours = BleUuids.encode(bytes)
            assertEquals(java.util.Base64.getEncoder().encodeToString(bytes), ours)
            assertArrayEquals(bytes, BleUuids.decode(ours))
        }
        assertThrows(IllegalArgumentException::class.java) { BleUuids.decode("@@@") }
    }

    @Test fun approvedDevicesPerAppAndType() {
        val dir = tmp.newFolder("state")
        val m = AppManifest.parse("""{"id":"bt","name":"BT","permissions":["bluetooth"]}""")
        val st = AppState(dir, m)
        assertFalse(st.isApproved("AA:BB:CC:DD:EE:FF", "ble"))
        st.approveDevice(AppState.Device("AA:BB:CC:DD:EE:FF", "ESP32", "ble"))
        assertTrue(st.isApproved("aa:bb:cc:dd:ee:ff", "ble"))
        assertFalse("тот же адрес, но как Serial — не разрешён", st.isApproved("AA:BB:CC:DD:EE:FF", "serial"))
        st.approveDevice(AppState.Device("AA:BB:CC:DD:EE:FF", "ESP32-new", "ble"))
        assertEquals(listOf("ESP32-new"), st.devices().map { it.name })
        // другое приложение не видит чужие устройства
        val other = AppState(dir, AppManifest.parse("""{"id":"other","name":"O","permissions":["bluetooth"]}"""))
        assertFalse(other.isApproved("AA:BB:CC:DD:EE:FF", "ble"))
        assertTrue(AppState(dir, m).isApproved("AA:BB:CC:DD:EE:FF", "ble"))
        st.forgetDevices()
        assertTrue(st.devices().isEmpty())
    }
}
