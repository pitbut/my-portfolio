package com.robutpit.pitbrowser.apps

import android.annotation.SuppressLint
import android.app.Activity
import android.app.AlertDialog
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothGatt
import android.bluetooth.BluetoothGattCallback
import android.bluetooth.BluetoothGattCharacteristic
import android.bluetooth.BluetoothGattDescriptor
import android.bluetooth.BluetoothGattServer
import android.bluetooth.BluetoothGattServerCallback
import android.bluetooth.BluetoothGattService
import android.bluetooth.BluetoothManager
import android.bluetooth.BluetoothProfile
import android.bluetooth.BluetoothStatusCodes
import android.bluetooth.le.AdvertiseCallback
import android.bluetooth.le.AdvertiseData
import android.bluetooth.le.AdvertiseSettings
import android.bluetooth.le.ScanCallback
import android.bluetooth.le.ScanFilter
import android.bluetooth.le.ScanResult
import android.bluetooth.le.ScanSettings
import android.content.Context
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.os.ParcelUuid
import android.view.ViewGroup
import android.widget.ArrayAdapter
import android.widget.FrameLayout
import android.widget.ListView
import android.widget.TextView
import org.json.JSONArray
import org.json.JSONObject

/**
 * PitLink: игры между телефонами по Bluetooth LE (до ~7 игроков, без интернета и сопряжения).
 * Хост создаёт комнату (GATT-сервер + реклама), игроки находят её в окне выбора и подключаются.
 * Сообщения игроков идут через хост: хост получает всё, а сообщения «всем» пересылает остальным.
 * Протокол пакетов — в LinkProtocol. Все методы и события — в главном потоке.
 */
@SuppressLint("MissingPermission") // разрешения проверяет AppActivity до вызова
class LinkBridge(
    private val activity: Activity,
    private val manifest: AppManifest,
    private val emit: (event: String, data: JSONObject) -> Unit,
) {
    class LinkException(message: String) : Exception(message)

    private val main = Handler(Looper.getMainLooper())
    private val manager = activity.getSystemService(Context.BLUETOOTH_SERVICE) as BluetoothManager
    private val serviceUuid = LinkProtocol.serviceUuid(manifest.id)

    private var roomName = ""
    private var myName = ""

    private fun player(id: String, name: String) = JSONObject().put("id", id).put("name", name)

    // ================================================================== хост

    private class Peer(val device: BluetoothDevice) {
        var id: String? = null
        var name = ""
        var mtu = 23
        var subscribed = false
        var sending = false
        val queue = ArrayDeque<ByteArray>()
        val assembler = LinkProtocol.Assembler()
    }

    private var server: BluetoothGattServer? = null
    private var dataChar: BluetoothGattCharacteristic? = null
    private var advertising: AdvertiseCallback? = null
    private val peers = linkedMapOf<String, Peer>() // адрес → игрок
    private var nextPlayer = 2
    private var hostDone: ((Result<JSONObject>) -> Unit)? = null

    val isHost get() = server != null

    fun host(room: String, playerName: String, done: (Result<JSONObject>) -> Unit) {
        if (server != null || client != null) return done(Result.failure(LinkException("сначала выйдите из текущей комнаты: pit.link.leave()")))
        val adapter = manager.adapter ?: return done(Result.failure(LinkException("на этом телефоне нет Bluetooth")))
        if (adapter.bluetoothLeAdvertiser == null || !adapter.isMultipleAdvertisementSupported) {
            return done(Result.failure(LinkException("этот телефон не умеет создавать комнаты — пусть комнату создаст другой игрок")))
        }
        myName = playerName
        roomName = String(LinkProtocol.roomNameBytes(room.ifBlank { playerName }), Charsets.UTF_8)
        val s = manager.openGattServer(activity, serverCallback) ?: return done(Result.failure(LinkException("не удалось открыть Bluetooth-сервер")))
        server = s
        hostDone = done
        val c = BluetoothGattCharacteristic(
            LinkProtocol.DATA_CHAR,
            BluetoothGattCharacteristic.PROPERTY_WRITE or BluetoothGattCharacteristic.PROPERTY_WRITE_NO_RESPONSE or BluetoothGattCharacteristic.PROPERTY_NOTIFY,
            BluetoothGattCharacteristic.PERMISSION_WRITE,
        )
        c.addDescriptor(BluetoothGattDescriptor(BleUuids.CCCD, BluetoothGattDescriptor.PERMISSION_READ or BluetoothGattDescriptor.PERMISSION_WRITE))
        dataChar = c
        val service = BluetoothGattService(serviceUuid, BluetoothGattService.SERVICE_TYPE_PRIMARY)
        service.addCharacteristic(c)
        if (!s.addService(service)) { closeHost(); done(Result.failure(LinkException("не удалось создать комнату"))) }
        // дальше — onServiceAdded → startAdvertising
    }

    private fun startAdvertising() {
        val adv = manager.adapter?.bluetoothLeAdvertiser ?: return
        val cb = object : AdvertiseCallback() {
            override fun onStartSuccess(settingsInEffect: AdvertiseSettings) {
                main.post {
                    hostDone?.invoke(Result.success(roomJson("host")))
                    hostDone = null
                }
            }
            override fun onStartFailure(errorCode: Int) {
                main.post {
                    val cb = hostDone
                    hostDone = null
                    if (cb != null) { closeHost(); cb(Result.failure(LinkException("не удалось создать комнату (код $errorCode)"))) }
                }
            }
        }
        advertising = cb
        adv.startAdvertising(
            AdvertiseSettings.Builder()
                .setAdvertiseMode(AdvertiseSettings.ADVERTISE_MODE_LOW_LATENCY)
                .setTxPowerLevel(AdvertiseSettings.ADVERTISE_TX_POWER_HIGH)
                .setConnectable(true)
                .build(),
            AdvertiseData.Builder().setIncludeDeviceName(false).addServiceUuid(ParcelUuid(serviceUuid)).build(),
            AdvertiseData.Builder().setIncludeDeviceName(false)
                .addManufacturerData(LinkProtocol.MANUFACTURER_ID, LinkProtocol.roomNameBytes(roomName)).build(),
            cb,
        )
    }

    private fun stopAdvertising() {
        advertising?.let { runCatching { manager.adapter?.bluetoothLeAdvertiser?.stopAdvertising(it) } }
        advertising = null
    }

    /** Закрыть комнату для новых игроков (например, игра началась) или снова открыть. */
    fun lock(locked: Boolean) {
        if (server == null) throw LinkException("вы не хост комнаты")
        if (locked) stopAdvertising() else if (advertising == null) startAdvertising()
    }

    private fun roomJson(you: String) = JSONObject().put("room", roomName).put("you", you).put("players", playersJson())

    private fun playersJson(): JSONArray {
        if (client != null) return JSONArray(clientPlayers.map { (id, name) -> player(id, name) })
        val arr = JSONArray().put(player("host", myName))
        peers.values.filter { it.id != null }.forEach { arr.put(player(it.id!!, it.name)) }
        return arr
    }

    private val serverCallback = object : BluetoothGattServerCallback() {
        override fun onServiceAdded(status: Int, service: BluetoothGattService) {
            main.post {
                if (status == BluetoothGatt.GATT_SUCCESS) startAdvertising()
                else hostDone?.let { cb -> hostDone = null; closeHost(); cb(Result.failure(LinkException("не удалось создать комнату (код $status)"))) }
            }
        }

        override fun onConnectionStateChange(device: BluetoothDevice, status: Int, newState: Int) {
            main.post {
                if (newState == BluetoothProfile.STATE_CONNECTED) {
                    peers.getOrPut(device.address) { Peer(device) }
                } else {
                    val p = peers.remove(device.address) ?: return@post
                    val id = p.id ?: return@post
                    emit("link:leave", JSONObject().put("player", player(id, p.name)))
                    broadcast(LinkProtocol.envelope("leave", JSONObject().put("player", player(id, p.name))), except = null)
                }
            }
        }

        override fun onMtuChanged(device: BluetoothDevice, mtu: Int) {
            main.post { peers[device.address]?.mtu = mtu }
        }

        override fun onDescriptorWriteRequest(
            device: BluetoothDevice, requestId: Int, descriptor: BluetoothGattDescriptor,
            preparedWrite: Boolean, responseNeeded: Boolean, offset: Int, value: ByteArray?,
        ) {
            if (responseNeeded) server?.sendResponse(device, requestId, BluetoothGatt.GATT_SUCCESS, 0, null)
            main.post { peers[device.address]?.let { it.subscribed = value != null && value.isNotEmpty() && value[0].toInt() != 0; pump(it) } }
        }

        override fun onDescriptorReadRequest(device: BluetoothDevice, requestId: Int, offset: Int, descriptor: BluetoothGattDescriptor) {
            val on = peers[device.address]?.subscribed == true
            server?.sendResponse(device, requestId, BluetoothGatt.GATT_SUCCESS, 0,
                if (on) BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE else BluetoothGattDescriptor.DISABLE_NOTIFICATION_VALUE)
        }

        override fun onCharacteristicWriteRequest(
            device: BluetoothDevice, requestId: Int, characteristic: BluetoothGattCharacteristic,
            preparedWrite: Boolean, responseNeeded: Boolean, offset: Int, value: ByteArray?,
        ) {
            if (responseNeeded) server?.sendResponse(device, requestId, BluetoothGatt.GATT_SUCCESS, 0, null)
            val packet = value ?: return
            main.post {
                val p = peers.getOrPut(device.address) { Peer(device) }
                p.assembler.feed(packet)?.let { LinkProtocol.parse(it) }?.let { fromPeer(p, it) }
            }
        }

        override fun onNotificationSent(device: BluetoothDevice, status: Int) {
            main.post { peers[device.address]?.let { it.sending = false; pump(it) } }
        }
    }

    /** Сообщение от игрока хосту. */
    private fun fromPeer(p: Peer, m: JSONObject) {
        when (m.optString("t")) {
            "hello" -> {
                if (p.id != null) return
                p.id = "p${nextPlayer++}"
                p.name = m.optString("name").take(30).ifBlank { "Игрок" }
                val me = player(p.id!!, p.name)
                sendTo(p, LinkProtocol.envelope("welcome", roomJson(p.id!!)))
                broadcast(LinkProtocol.envelope("join", JSONObject().put("player", me)), except = p)
                emit("link:join", JSONObject().put("player", me))
            }
            "msg" -> {
                val id = p.id ?: return
                val data = m.opt("data") ?: JSONObject.NULL
                val to = m.optString("to", "host")
                val relay = LinkProtocol.envelope("msg", JSONObject().put("from", id).put("data", data))
                when {
                    to == "host" -> emit("link:message", JSONObject().put("from", id).put("data", data))
                    to == "all" -> { emit("link:message", JSONObject().put("from", id).put("data", data)); broadcast(relay, except = p) }
                    else -> peers.values.find { it.id == to }?.let { sendTo(it, relay) }
                }
            }
        }
    }

    private fun broadcast(bytes: ByteArray, except: Peer?) {
        peers.values.filter { it !== except && it.id != null }.forEach { sendTo(it, bytes) }
    }

    private fun sendTo(p: Peer, bytes: ByteArray) {
        p.queue.addAll(LinkProtocol.split(bytes, p.mtu))
        pump(p)
    }

    /** Уведомления одному устройству отправляются строго по одному — ждём onNotificationSent. */
    private fun pump(p: Peer) {
        if (p.sending || !p.subscribed) return
        val packet = p.queue.removeFirstOrNull() ?: return
        val s = server ?: return
        val c = dataChar ?: return
        val ok = if (Build.VERSION.SDK_INT >= 33) {
            s.notifyCharacteristicChanged(p.device, c, false, packet) == BluetoothStatusCodes.SUCCESS
        } else {
            @Suppress("DEPRECATION")
            run { c.value = packet; s.notifyCharacteristicChanged(p.device, c, false) }
        }
        if (ok) p.sending = true
        else { p.queue.addFirst(packet); main.postDelayed({ pump(p) }, 15) } // буфер занят — чуть позже
    }

    private fun closeHost() {
        stopAdvertising()
        val s = server
        server = null
        peers.values.forEach { runCatching { s?.cancelConnection(it.device) } }
        peers.clear()
        runCatching { s?.close() }
        dataChar = null
        nextPlayer = 2
    }

    // ================================================================== игрок

    private var client: BluetoothGatt? = null
    private var clientChar: BluetoothGattCharacteristic? = null
    private var clientMtu = 23
    private var clientWriting = false
    private val clientQueue = ArrayDeque<ByteArray>()
    private val clientAssembler = LinkProtocol.Assembler()
    private var joinDone: ((Result<JSONObject>) -> Unit)? = null
    private var myId = ""
    private val clientPlayers = linkedMapOf<String, String>() // id → имя
    private var scanCb: ScanCallback? = null

    /** Окно выбора комнаты этой игры поблизости → подключение. */
    fun join(playerName: String, done: (Result<JSONObject>) -> Unit) {
        if (server != null || client != null) return done(Result.failure(LinkException("сначала выйдите из текущей комнаты: pit.link.leave()")))
        val scanner = manager.adapter?.bluetoothLeScanner ?: return done(Result.failure(LinkException("Bluetooth выключен")))
        myName = playerName
        val rooms = linkedMapOf<String, Pair<BluetoothDevice, String>>()
        val labels = ArrayList<String>()
        val empty = TextView(activity).apply {
            text = "Ищем комнаты «${manifest.name}» рядом…\nПопросите друга нажать «Создать комнату»."
            setPadding(60, 40, 60, 40)
        }
        val list = ListView(activity).apply { emptyView = empty }
        val adapter = object : ArrayAdapter<String>(activity, android.R.layout.simple_list_item_1, labels) {
            override fun getView(position: Int, convertView: android.view.View?, parent: ViewGroup) =
                super.getView(position, convertView, parent).also { (it as TextView).text = rooms.values.elementAt(position).second }
        }
        list.adapter = adapter
        var finished = false
        lateinit var dialog: AlertDialog
        fun finish(r: Result<JSONObject>?) {
            if (finished) return
            finished = true
            scanCb?.let { runCatching { scanner.stopScan(it) } }
            scanCb = null
            r?.let(done)
        }
        val cb = object : ScanCallback() {
            override fun onScanResult(callbackType: Int, result: ScanResult) {
                val bytes = result.scanRecord?.getManufacturerSpecificData(LinkProtocol.MANUFACTURER_ID)
                val name = bytes?.let { String(it, Charsets.UTF_8) } ?: "Комната"
                main.post {
                    if (finished) return@post
                    val isNew = result.device.address !in rooms
                    rooms[result.device.address] = result.device to name
                    if (isNew) labels.add(result.device.address)
                    adapter.notifyDataSetChanged()
                }
            }
            override fun onScanFailed(errorCode: Int) {
                main.post { empty.text = "Не удалось начать поиск (код $errorCode)" }
            }
        }
        scanCb = cb
        scanner.startScan(
            listOf(ScanFilter.Builder().setServiceUuid(ParcelUuid(serviceUuid)).build()),
            ScanSettings.Builder().setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY).build(),
            cb,
        )
        dialog = AlertDialog.Builder(activity)
            .setTitle("${manifest.name}: комнаты рядом")
            .setView(FrameLayout(activity).apply { addView(list); addView(empty) })
            .setNegativeButton("Отмена") { _, _ -> finish(Result.failure(LinkException("пользователь отменил выбор"))) }
            .setOnCancelListener { finish(Result.failure(LinkException("пользователь отменил выбор"))) }
            .create()
        list.setOnItemClickListener { _, _, pos, _ ->
            val (dev, name) = rooms.values.elementAt(pos)
            dialog.dismiss()
            finish(null)
            connect(dev, name, done)
        }
        dialog.show()
    }

    private var joinAttempt = 0

    private fun connect(dev: BluetoothDevice, name: String, done: (Result<JSONObject>) -> Unit) {
        roomName = name
        joinDone = done
        val attempt = ++joinAttempt
        client = dev.connectGatt(activity, false, clientCallback, BluetoothDevice.TRANSPORT_LE)
        main.postDelayed({ if (attempt == joinAttempt) failJoin("комната не отвечает — подойдите ближе и попробуйте снова") }, 15_000)
    }

    private fun failJoin(message: String) {
        val cb = joinDone ?: return
        joinDone = null
        closeClient()
        cb(Result.failure(LinkException(message)))
    }

    private val clientCallback = object : BluetoothGattCallback() {
        override fun onConnectionStateChange(g: BluetoothGatt, status: Int, newState: Int) {
            main.post {
                if (newState == BluetoothProfile.STATE_CONNECTED && status == BluetoothGatt.GATT_SUCCESS) {
                    if (!g.requestMtu(247)) g.discoverServices()
                } else if (joinDone != null) {
                    failJoin("не удалось подключиться к комнате (код $status)")
                } else if (client != null) {
                    closeClient()
                    emit("link:closed", JSONObject().put("reason", "соединение с комнатой потеряно"))
                }
            }
        }

        override fun onMtuChanged(g: BluetoothGatt, mtu: Int, status: Int) {
            main.post { if (status == BluetoothGatt.GATT_SUCCESS) clientMtu = mtu; g.discoverServices() }
        }

        override fun onServicesDiscovered(g: BluetoothGatt, status: Int) {
            main.post {
                val c = g.getService(serviceUuid)?.getCharacteristic(LinkProtocol.DATA_CHAR)
                    ?: return@post failJoin("это не комната этой игры")
                clientChar = c
                g.setCharacteristicNotification(c, true)
                val d = c.getDescriptor(BleUuids.CCCD) ?: return@post failJoin("комната не поддерживает уведомления")
                val ok = if (Build.VERSION.SDK_INT >= 33) {
                    g.writeDescriptor(d, BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE) == BluetoothStatusCodes.SUCCESS
                } else {
                    @Suppress("DEPRECATION")
                    run { d.value = BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE; g.writeDescriptor(d) }
                }
                if (!ok) failJoin("не удалось подписаться на сообщения комнаты")
            }
        }

        override fun onDescriptorWrite(g: BluetoothGatt, d: BluetoothGattDescriptor, status: Int) {
            // подписались — представляемся хосту
            main.post { clientSend(LinkProtocol.envelope("hello", JSONObject().put("name", myName))) }
        }

        override fun onCharacteristicWrite(g: BluetoothGatt, c: BluetoothGattCharacteristic, status: Int) {
            main.post { clientWriting = false; clientPump() }
        }

        @Deprecated("Deprecated in Java")
        override fun onCharacteristicChanged(g: BluetoothGatt, c: BluetoothGattCharacteristic) {
            if (Build.VERSION.SDK_INT < 33) {
                @Suppress("DEPRECATION") val v = c.value ?: return
                main.post { fromHost(v) }
            }
        }

        override fun onCharacteristicChanged(g: BluetoothGatt, c: BluetoothGattCharacteristic, value: ByteArray) {
            main.post { fromHost(value) }
        }
    }

    private fun fromHost(packet: ByteArray) {
        val m = clientAssembler.feed(packet)?.let { LinkProtocol.parse(it) } ?: return
        when (m.optString("t")) {
            "welcome" -> {
                myId = m.optString("you")
                clientPlayers.clear()
                m.optJSONArray("players")?.let { a -> for (i in 0 until a.length()) a.optJSONObject(i)?.let { clientPlayers[it.optString("id")] = it.optString("name") } }
                joinDone?.invoke(Result.success(roomJson(myId)))
                joinDone = null
            }
            "join" -> m.optJSONObject("player")?.let { clientPlayers[it.optString("id")] = it.optString("name"); emit("link:join", JSONObject().put("player", it)) }
            "leave" -> m.optJSONObject("player")?.let { clientPlayers.remove(it.optString("id")); emit("link:leave", JSONObject().put("player", it)) }
            "msg" -> emit("link:message", JSONObject().put("from", m.optString("from", "host")).put("data", m.opt("data") ?: JSONObject.NULL))
        }
    }

    private fun clientSend(bytes: ByteArray) {
        clientQueue.addAll(LinkProtocol.split(bytes, clientMtu))
        clientPump()
    }

    /** Запись без ответа, но строго по одной — Android сообщает в onCharacteristicWrite, когда можно следующую. */
    private fun clientPump() {
        if (clientWriting) return
        val g = client ?: return
        val c = clientChar ?: return
        val packet = clientQueue.removeFirstOrNull() ?: return
        val type = BluetoothGattCharacteristic.WRITE_TYPE_NO_RESPONSE
        val ok = if (Build.VERSION.SDK_INT >= 33) {
            g.writeCharacteristic(c, packet, type) == BluetoothStatusCodes.SUCCESS
        } else {
            @Suppress("DEPRECATION")
            run { c.writeType = type; c.value = packet; g.writeCharacteristic(c) }
        }
        if (ok) clientWriting = true
        else { clientQueue.addFirst(packet); main.postDelayed({ clientPump() }, 15) }
    }

    private fun closeClient() {
        val g = client
        client = null
        clientChar = null
        clientQueue.clear()
        clientWriting = false
        clientPlayers.clear()
        g?.let { runCatching { it.disconnect() }; runCatching { it.close() } }
    }

    // ================================================================== общее

    /** Отправить игровое сообщение. Хост: всем или одному игроку. Игрок: хосту, всем или одному. */
    fun send(data: Any, to: String?) {
        when {
            server != null -> {
                val env = LinkProtocol.envelope("msg", JSONObject().put("from", "host").put("data", data))
                if (to == null || to == "all") broadcast(env, except = null)
                else peers.values.find { it.id == to }?.let { sendTo(it, env) } ?: throw LinkException("нет игрока $to")
            }
            client != null -> {
                if (joinDone != null) throw LinkException("ещё подключаемся к комнате")
                clientSend(LinkProtocol.envelope("msg", JSONObject().put("to", to ?: "host").put("data", data)))
            }
            else -> throw LinkException("вы не в комнате — сначала pit.link.host() или pit.link.join()")
        }
    }

    fun players(): JSONArray = if (server == null && client == null) JSONArray() else playersJson()

    fun leave() {
        if (server != null) closeHost()
        if (client != null) closeClient()
        joinDone = null
        hostDone = null
    }
}
