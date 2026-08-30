package com.robutpit.roachrace.bluetooth

import android.annotation.SuppressLint
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothManager
import android.bluetooth.BluetoothServerSocket
import android.bluetooth.BluetoothSocket
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import java.io.BufferedReader
import java.io.IOException
import java.io.InputStreamReader
import java.io.OutputStream
import java.util.UUID

/**
 * Two-phone "individual mode" link over classic Bluetooth RFCOMM: one phone
 * hosts (authoritative race simulation), the other joins and only renders
 * the state the host streams to it, so both screens show the same shared
 * field. This is real Android Bluetooth API usage, but it has only been
 * exercised in code review here — it has not been paired-tested on two
 * physical phones, so treat first runs as a beta and report anything odd.
 */
private val APP_UUID: UUID = UUID.fromString("7a2c5b6e-2f36-4b7a-9b6d-3b2f6f0b7a11")

sealed class LinkState {
    data object Idle : LinkState()
    data object Listening : LinkState()
    data object Connecting : LinkState()
    data class Connected(val peerName: String) : LinkState()
    data class Failed(val reason: String) : LinkState()
}

@SuppressLint("MissingPermission")
fun deviceLabel(device: BluetoothDevice): String =
    try {
        device.name ?: device.address
    } catch (_: SecurityException) {
        device.address
    }

class BtRaceLink(private val appContext: Context) {

    private val btManager = appContext.getSystemService(Context.BLUETOOTH_SERVICE) as? BluetoothManager
    val adapter: BluetoothAdapter? = btManager?.adapter

    val state = mutableStateOf<LinkState>(LinkState.Idle)
    val discoveredDevices = mutableStateListOf<BluetoothDevice>()
    var onLine: ((String) -> Unit)? = null

    private var serverSocket: BluetoothServerSocket? = null
    private var socket: BluetoothSocket? = null
    private var output: OutputStream? = null
    private var readThread: Thread? = null
    private var acceptThread: Thread? = null
    @Volatile private var closing = false

    private val discoveryReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) {
            if (intent.action == BluetoothDevice.ACTION_FOUND) {
                val device = intent.getParcelableExtra<BluetoothDevice>(BluetoothDevice.EXTRA_DEVICE)
                if (device != null && discoveredDevices.none { it.address == device.address }) {
                    discoveredDevices.add(device)
                }
            }
        }
    }
    private var receiverRegistered = false

    fun isBluetoothEnabled(): Boolean = adapter?.isEnabled == true

    @SuppressLint("MissingPermission")
    fun bondedDevices(): List<BluetoothDevice> =
        try {
            adapter?.bondedDevices?.toList() ?: emptyList()
        } catch (_: SecurityException) {
            emptyList()
        }

    @SuppressLint("MissingPermission")
    fun startDiscovery() {
        val a = adapter ?: return
        if (!receiverRegistered) {
            appContext.registerReceiver(discoveryReceiver, IntentFilter(BluetoothDevice.ACTION_FOUND))
            receiverRegistered = true
        }
        discoveredDevices.clear()
        try {
            a.startDiscovery()
        } catch (_: SecurityException) {
        }
    }

    @SuppressLint("MissingPermission")
    fun stopDiscovery() {
        try {
            adapter?.cancelDiscovery()
        } catch (_: SecurityException) {
        }
    }

    @SuppressLint("MissingPermission")
    fun startHosting() {
        val a = adapter ?: run { state.value = LinkState.Failed("Bluetooth недоступен"); return }
        closing = false
        state.value = LinkState.Listening
        acceptThread = Thread {
            try {
                val server = a.listenUsingInsecureRfcommWithServiceRecord("RoachRace", APP_UUID)
                serverSocket = server
                val s = server.accept()
                serverSocket = null
                try { server.close() } catch (_: IOException) {}
                onConnected(s)
            } catch (e: IOException) {
                if (!closing) state.value = LinkState.Failed(e.message ?: "Ошибка подключения")
            }
        }
        acceptThread?.start()
    }

    @SuppressLint("MissingPermission")
    fun connectTo(device: BluetoothDevice) {
        closing = false
        state.value = LinkState.Connecting
        stopDiscovery()
        Thread {
            try {
                val s = device.createInsecureRfcommSocketToServiceRecord(APP_UUID)
                s.connect()
                onConnected(s)
            } catch (e: IOException) {
                if (!closing) state.value = LinkState.Failed(e.message ?: "Не удалось подключиться")
            }
        }.start()
    }

    @SuppressLint("MissingPermission")
    private fun onConnected(s: BluetoothSocket) {
        socket = s
        output = s.outputStream
        val peerName = try { s.remoteDevice.name ?: "Соперник" } catch (_: SecurityException) { "Соперник" }
        state.value = LinkState.Connected(peerName)
        readThread = Thread {
            try {
                val reader = BufferedReader(InputStreamReader(s.inputStream))
                while (!closing) {
                    val line = reader.readLine() ?: break
                    onLine?.invoke(line)
                }
            } catch (e: IOException) {
                if (!closing) state.value = LinkState.Failed("Соединение прервано")
            }
        }
        readThread?.start()
    }

    fun send(line: String) {
        val out = output ?: return
        try {
            out.write((line + "\n").toByteArray(Charsets.UTF_8))
            out.flush()
        } catch (_: IOException) {
        }
    }

    fun close() {
        closing = true
        try { serverSocket?.close() } catch (_: IOException) {}
        try { socket?.close() } catch (_: IOException) {}
        if (receiverRegistered) {
            try { appContext.unregisterReceiver(discoveryReceiver) } catch (_: IllegalArgumentException) {}
            receiverRegistered = false
        }
        stopDiscovery()
        socket = null
        output = null
        state.value = LinkState.Idle
    }
}
