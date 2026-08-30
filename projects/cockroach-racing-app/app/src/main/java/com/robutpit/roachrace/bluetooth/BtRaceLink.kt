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
import java.util.UUID
import java.util.concurrent.LinkedBlockingQueue

/**
 * Bluetooth Classic RFCOMM link for the "individual mode" tournament: one
 * phone hosts (authoritative race simulation), and any number of other
 * phones join — a star topology, since RFCOMM has no direct joiner-to-joiner
 * link. The host keeps accepting new connections (up to [MAX_PEERS]) until
 * it starts the race, then streams state to everyone. This is real Android
 * Bluetooth API usage, exercised in code review and on real hardware for
 * the 2-phone case; 3+ phones is new and unverified — report anything odd.
 */
private val APP_UUID: UUID = UUID.fromString("7a2c5b6e-2f36-4b7a-9b6d-3b2f6f0b7a11")
const val MAX_PEERS = 5

sealed class LinkState {
    data object Idle : LinkState()
    data object Listening : LinkState()
    data object Connecting : LinkState()
    data class Connected(val peerName: String) : LinkState()
    data class Failed(val reason: String) : LinkState()
}

/** One connected peer, from the host's point of view. [id] is also that
 * peer's assigned racer index (1..N; the host itself is always racer 0). */
class HostPeer(val id: Int, val displayName: String, private val socket: BluetoothSocket, private val onLine: (Int, String) -> Unit, private val onFail: (Int) -> Unit) {
    private val output = socket.outputStream
    private val writeQueue = LinkedBlockingQueue<String>()
    @Volatile private var closing = false
    private var readThread: Thread? = null
    private var writeThread: Thread? = null

    fun start() {
        readThread = Thread {
            try {
                val reader = BufferedReader(InputStreamReader(socket.inputStream))
                while (!closing) {
                    val line = reader.readLine() ?: break
                    onLine(id, line)
                }
                if (!closing) onFail(id)
            } catch (e: IOException) {
                if (!closing) onFail(id)
            }
        }
        writeThread = Thread {
            try {
                while (!closing) {
                    val line = writeQueue.take()
                    if (closing) break
                    output.write((line + "\n").toByteArray(Charsets.UTF_8))
                    output.flush()
                }
            } catch (_: InterruptedException) {
            } catch (e: IOException) {
                if (!closing) onFail(id)
            }
        }
        readThread?.start()
        writeThread?.start()
    }

    fun send(line: String) {
        writeQueue.offer(line)
    }

    fun close() {
        closing = true
        writeThread?.interrupt()
        try { socket.close() } catch (_: IOException) {}
    }
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

    /** Idle/Listening/Failed while hosting; Connecting/Connected/Failed while joining. */
    val state = mutableStateOf<LinkState>(LinkState.Idle)
    val discoveredDevices = mutableStateListOf<BluetoothDevice>()

    /** Host-side: everyone currently connected, in join order. Empty when
     * acting as a joiner (a joiner only ever talks to the host). */
    val hostPeers = mutableStateListOf<HostPeer>()

    /** line callback: (peerId, line). peerId is always 0 for a joiner's
     * single connection to the host; on the host it's the sender's assigned
     * racer index (1..N). */
    var onLine: ((Int, String) -> Unit)? = null

    private var serverSocket: BluetoothServerSocket? = null
    private var acceptThread: Thread? = null
    @Volatile private var accepting = false
    private var nextPeerId = 1

    // Joiner-side single connection
    private var joinPeer: HostPeer? = null

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

    /** Starts listening and keeps accepting new joiners (up to [MAX_PEERS])
     * until [stopAcceptingNewPeers] is called — e.g. when the host presses
     * "start race". Existing connections are unaffected by that call. */
    @SuppressLint("MissingPermission")
    fun startHosting() {
        val a = adapter ?: run { state.value = LinkState.Failed("Bluetooth недоступен"); return }
        if (!a.isEnabled) { state.value = LinkState.Failed("Bluetooth выключен"); return }
        hostPeers.clear()
        nextPeerId = 1
        accepting = true
        state.value = LinkState.Listening
        acceptThread = Thread {
            try {
                val server = a.listenUsingInsecureRfcommWithServiceRecord("RoachRace", APP_UUID)
                serverSocket = server
                while (accepting && hostPeers.size < MAX_PEERS) {
                    val s = try {
                        server.accept(120_000)
                    } catch (e: IOException) {
                        if (accepting) {
                            val timedOut = e.message?.contains("time", ignoreCase = true) == true
                            if (hostPeers.isEmpty()) {
                                state.value = LinkState.Failed(
                                    if (timedOut) "Никто не подключился за 2 минуты — проверь, что на втором телефоне тоже включён Bluetooth и нажато «Присоединиться»"
                                    else (e.message ?: "Ошибка подключения"),
                                )
                            }
                        }
                        break
                    }
                    val id = nextPeerId++
                    val name = try { s.remoteDevice.name ?: "Игрок $id" } catch (_: SecurityException) { "Игрок $id" }
                    val peer = HostPeer(id, name, s, onLine = { pid, line -> onLine?.invoke(pid, line) }, onFail = { pid -> onPeerFailed(pid) })
                    hostPeers.add(peer)
                    peer.start()
                    peer.send(RaceProtocol.welcome(id))
                }
            } catch (e: IOException) {
                if (accepting && hostPeers.isEmpty()) state.value = LinkState.Failed(e.message ?: "Ошибка подключения")
            } catch (e: SecurityException) {
                if (accepting && hostPeers.isEmpty()) state.value = LinkState.Failed("Нет разрешения на Bluetooth — проверь разрешения приложения в настройках телефона")
            }
        }
        acceptThread?.start()
    }

    private fun onPeerFailed(id: Int) {
        hostPeers.removeAll { it.id == id }
    }

    /** Stops accepting *new* joiners (called once the host starts the race)
     * without touching peers already connected. */
    fun stopAcceptingNewPeers() {
        accepting = false
        try { serverSocket?.close() } catch (_: IOException) {}
    }

    fun sendToAll(line: String) {
        hostPeers.forEach { it.send(line) }
    }

    fun sendToPeer(id: Int, line: String) {
        hostPeers.find { it.id == id }?.send(line)
    }

    @SuppressLint("MissingPermission")
    fun connectTo(device: BluetoothDevice) {
        val a = adapter ?: run { state.value = LinkState.Failed("Bluetooth недоступен"); return }
        if (!a.isEnabled) { state.value = LinkState.Failed("Bluetooth выключен"); return }
        state.value = LinkState.Connecting
        stopDiscovery()
        Thread {
            try {
                val s = device.createInsecureRfcommSocketToServiceRecord(APP_UUID)
                s.connect()
                val peerName = try { s.remoteDevice.name ?: "Хост" } catch (_: SecurityException) { "Хост" }
                val peer = HostPeer(
                    0, peerName, s,
                    onLine = { _, line -> onLine?.invoke(0, line) },
                    onFail = { state.value = LinkState.Failed("Соединение прервано") },
                )
                joinPeer = peer
                peer.start()
                state.value = LinkState.Connected(peerName)
            } catch (e: IOException) {
                state.value = LinkState.Failed(
                    "Не удалось подключиться (${e.message ?: "нет ответа"}). " +
                        "Убедись, что на телефоне-хосте открыт экран «Создать игру» и он ждёт подключения.",
                )
            } catch (e: SecurityException) {
                state.value = LinkState.Failed("Нет разрешения на Bluetooth — проверь разрешения приложения в настройках телефона")
            }
        }.start()
    }

    /** Non-blocking: queues the line on the joiner's single connection to the host. */
    fun send(line: String) {
        joinPeer?.send(line)
    }

    fun close() {
        accepting = false
        try { serverSocket?.close() } catch (_: IOException) {}
        hostPeers.forEach { it.close() }
        hostPeers.clear()
        joinPeer?.close()
        joinPeer = null
        if (receiverRegistered) {
            try { appContext.unregisterReceiver(discoveryReceiver) } catch (_: IllegalArgumentException) {}
            receiverRegistered = false
        }
        stopDiscovery()
        state.value = LinkState.Idle
    }
}
