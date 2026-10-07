package com.robutpit.pitbrowser.apps

import android.annotation.SuppressLint
import android.app.Activity
import android.app.AlertDialog
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothGatt
import android.bluetooth.BluetoothGattCallback
import android.bluetooth.BluetoothGattCharacteristic
import android.bluetooth.BluetoothGattDescriptor
import android.bluetooth.BluetoothManager
import android.bluetooth.BluetoothProfile
import android.bluetooth.BluetoothSocket
import android.bluetooth.BluetoothStatusCodes
import android.bluetooth.le.ScanCallback
import android.bluetooth.le.ScanFilter
import android.bluetooth.le.ScanResult
import android.bluetooth.le.ScanSettings
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.os.ParcelUuid
import android.view.ViewGroup
import android.widget.ArrayAdapter
import android.widget.ListView
import android.widget.TextView
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.util.UUID
import java.util.concurrent.Executors

/**
 * Bluetooth для PitSDK.
 *
 * BLE (Bluetooth Low Energy): браслеты, пульсометры, датчики, ESP32/nRF, самодельные контроллеры.
 * Serial (классический SPP): HC-05/HC-06, ESP32 BluetoothSerial.
 *
 * Как в Web Bluetooth, приложение получает доступ только к устройствам, которые пользователь сам
 * выбрал в окне выбора; выбор запоминается для этого приложения.
 * Все методы вызываются в главном потоке; ответы и события — тоже в главном потоке.
 */
@SuppressLint("MissingPermission") // разрешения проверяет AppActivity до вызова любых методов
class BluetoothBridge(
    private val activity: Activity,
    private val state: AppState,
    private val emit: (event: String, data: JSONObject) -> Unit,
) {
    class BtException(message: String) : Exception(message)

    private val main = Handler(Looper.getMainLooper())
    private val io = Executors.newCachedThreadPool()
    private val manager = activity.getSystemService(Context.BLUETOOTH_SERVICE) as? BluetoothManager
    private val adapter: BluetoothAdapter? get() = manager?.adapter

    fun supported() = adapter != null
    fun enabled() = adapter?.isEnabled == true

    fun status() = JSONObject()
        .put("supported", supported())
        .put("enabled", enabled())
        .put("ble", activity.packageManager.hasSystemFeature("android.hardware.bluetooth_le"))
        .put("classic", activity.packageManager.hasSystemFeature("android.hardware.bluetooth"))

    private fun requireAdapter(): BluetoothAdapter {
        val a = adapter ?: throw BtException("на этом телефоне нет Bluetooth")
        if (!a.isEnabled) throw BtException("Bluetooth выключен")
        return a
    }

    private fun deviceJson(d: AppState.Device) = JSONObject().put("id", d.id).put("name", d.name).put("type", d.type)

    fun approvedDevices(): JSONArray = JSONArray().apply { state.devices().forEach { put(deviceJson(it)) } }

    // ================================================================== окно выбора BLE-устройства

    private var scanner: ScanCallback? = null

    /**
     * Ищет устройства и показывает список; пользователь выбирает одно.
     * filters: services — только устройства с этими сервисами, namePrefix — имя начинается с…
     */
    fun requestDevice(services: List<UUID>, namePrefix: String?, done: (Result<JSONObject>) -> Unit) {
        val a = try { requireAdapter() } catch (e: BtException) { return done(Result.failure(e)) }
        val le = a.bluetoothLeScanner ?: return done(Result.failure(BtException("BLE недоступен")))
        val found = linkedMapOf<String, Pair<BluetoothDevice, Int>>() // адрес → устройство, сигнал
        val labels = ArrayList<String>()
        val list = ListView(activity)
        val empty = TextView(activity).apply {
            text = "Поиск устройств…\nУбедитесь, что устройство включено и находится рядом."
            setPadding(60, 40, 60, 40)
        }
        list.emptyView = empty
        list.adapter = object : ArrayAdapter<String>(activity, android.R.layout.simple_list_item_2, android.R.id.text1, labels) {
            override fun getView(position: Int, convertView: android.view.View?, parent: ViewGroup): android.view.View {
                val v = super.getView(position, convertView, parent)
                val (dev, rssi) = found.values.elementAt(position)
                v.findViewById<TextView>(android.R.id.text1).text = dev.name ?: "Без имени"
                v.findViewById<TextView>(android.R.id.text2).text = "${dev.address} · сигнал ${signal(rssi)}"
                return v
            }
        }
        val container = android.widget.FrameLayout(activity).apply {
            addView(list)
            addView(empty)
        }
        var finished = false
        lateinit var dialog: AlertDialog
        fun finish(r: Result<JSONObject>) {
            if (finished) return
            finished = true
            stopScan(le)
            done(r)
        }
        val cb = object : ScanCallback() {
            override fun onScanResult(callbackType: Int, result: ScanResult) {
                val dev = result.device
                val name = result.scanRecord?.deviceName ?: dev.name
                if (namePrefix != null && name?.startsWith(namePrefix) != true) return
                main.post {
                    val isNew = dev.address !in found
                    found[dev.address] = dev to result.rssi
                    if (isNew) labels.add(dev.address)
                    (list.adapter as ArrayAdapter<*>).notifyDataSetChanged()
                }
            }
            override fun onScanFailed(errorCode: Int) {
                main.post { empty.text = "Не удалось начать поиск (код $errorCode). Выключите и включите Bluetooth." }
            }
        }
        scanner = cb
        val filters = services.map { ScanFilter.Builder().setServiceUuid(ParcelUuid(it)).build() }
        le.startScan(filters.ifEmpty { null }, ScanSettings.Builder().setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY).build(), cb)
        main.postDelayed({ if (!finished) { stopScan(le); if (found.isEmpty()) empty.text = "Устройства не найдены.\nНа Android 11 и старше для поиска должна быть включена геолокация." } }, SCAN_TIME_MS)

        dialog = AlertDialog.Builder(activity)
            .setTitle("${state.manifest.name}: выберите устройство")
            .setView(container)
            .setNegativeButton("Отмена") { _, _ -> finish(Result.failure(BtException("пользователь отменил выбор"))) }
            .setOnCancelListener { finish(Result.failure(BtException("пользователь отменил выбор"))) }
            .create()
        list.setOnItemClickListener { _, _, pos, _ ->
            val (dev, _) = found.values.elementAt(pos)
            val d = AppState.Device(dev.address, dev.name ?: "Без имени", TYPE_BLE)
            state.approveDevice(d)
            dialog.dismiss()
            finish(Result.success(deviceJson(d)))
        }
        dialog.show()
    }

    private fun stopScan(le: android.bluetooth.le.BluetoothLeScanner) {
        scanner?.let { runCatching { le.stopScan(it) } }
        scanner = null
    }

    private fun signal(rssi: Int) = when {
        rssi >= -60 -> "отличный"
        rssi >= -75 -> "хороший"
        rssi >= -90 -> "слабый"
        else -> "очень слабый"
    }

    // ================================================================== BLE: подключение и GATT

    /** Операции GATT в Android нельзя запускать параллельно — у каждого подключения своя очередь. */
    private inner class Conn(val id: String) : BluetoothGattCallback() {
        var gatt: BluetoothGatt? = null
        var onConnected: ((Result<JSONObject>) -> Unit)? = null
        val queue = ArrayDeque<Op>()
        var current: Op? = null

        override fun onConnectionStateChange(g: BluetoothGatt, status: Int, newState: Int) {
            main.post {
                if (newState == BluetoothProfile.STATE_CONNECTED && status == BluetoothGatt.GATT_SUCCESS) {
                    // больше данных за один пакет (по умолчанию всего 20 байт)
                    if (!g.requestMtu(247)) g.discoverServices()
                    return@post
                }
                val connecting = onConnected
                onConnected = null
                closeConn(this)
                if (connecting != null) {
                    connecting(Result.failure(BtException("не удалось подключиться (код $status). Попробуйте ещё раз.")))
                } else {
                    emit("bluetooth:disconnected", JSONObject().put("device", id))
                }
            }
        }

        override fun onMtuChanged(g: BluetoothGatt, mtu: Int, status: Int) {
            main.post { g.discoverServices() }
        }

        override fun onServicesDiscovered(g: BluetoothGatt, status: Int) {
            main.post {
                val cb = onConnected ?: return@post
                onConnected = null
                if (status != BluetoothGatt.GATT_SUCCESS) {
                    closeConn(this)
                    cb(Result.failure(BtException("не удалось получить список сервисов (код $status)")))
                } else {
                    cb(Result.success(JSONObject().put("device", id).put("services", servicesJson(g))))
                }
            }
        }

        // Android 13+ вызывает варианты с value, старые версии — устаревшие варианты без него.
        @Deprecated("Deprecated in Java")
        override fun onCharacteristicRead(g: BluetoothGatt, c: BluetoothGattCharacteristic, status: Int) {
            if (Build.VERSION.SDK_INT < 33) {
                @Suppress("DEPRECATION") val v = c.value ?: ByteArray(0)
                main.post { complete(this, status, v) }
            }
        }

        override fun onCharacteristicRead(g: BluetoothGatt, c: BluetoothGattCharacteristic, value: ByteArray, status: Int) {
            main.post { complete(this, status, value) }
        }

        override fun onCharacteristicWrite(g: BluetoothGatt, c: BluetoothGattCharacteristic, status: Int) {
            main.post { complete(this, status, null) }
        }

        override fun onDescriptorWrite(g: BluetoothGatt, d: BluetoothGattDescriptor, status: Int) {
            main.post { complete(this, status, null) }
        }

        @Deprecated("Deprecated in Java")
        override fun onCharacteristicChanged(g: BluetoothGatt, c: BluetoothGattCharacteristic) {
            if (Build.VERSION.SDK_INT < 33) {
                @Suppress("DEPRECATION") val v = c.value ?: ByteArray(0)
                main.post { notify(c, v) }
            }
        }

        override fun onCharacteristicChanged(g: BluetoothGatt, c: BluetoothGattCharacteristic, value: ByteArray) {
            main.post { notify(c, value) }
        }

        private fun notify(c: BluetoothGattCharacteristic, value: ByteArray) {
            emit(
                "bluetooth:notify",
                JSONObject()
                    .put("device", id)
                    .put("service", BleUuids.format(c.service.uuid))
                    .put("characteristic", BleUuids.format(c.uuid))
                    .put("value", BleUuids.encode(value)),
            )
        }
    }

    private class Op(val start: () -> Boolean, val done: (Result<ByteArray?>) -> Unit) {
        var timeout: Runnable? = null
    }

    private val conns = mutableMapOf<String, Conn>()

    fun connect(id: String, done: (Result<JSONObject>) -> Unit) {
        if (!state.isApproved(id, TYPE_BLE)) return done(Result.failure(BtException("устройство не выбрано пользователем — сначала pit.bluetooth.requestDevice()")))
        val a = try { requireAdapter() } catch (e: BtException) { return done(Result.failure(e)) }
        conns[id]?.gatt?.let { g -> return done(Result.success(JSONObject().put("device", id).put("services", servicesJson(g)))) }
        val dev = runCatching { a.getRemoteDevice(id.uppercase()) }.getOrNull() ?: return done(Result.failure(BtException("неверный адрес устройства")))
        val conn = Conn(id)
        conns[id] = conn
        conn.onConnected = done
        conn.gatt = dev.connectGatt(activity, false, conn, BluetoothDevice.TRANSPORT_LE)
        main.postDelayed({
            conn.onConnected?.let { cb ->
                conn.onConnected = null
                closeConn(conn)
                cb(Result.failure(BtException("устройство не отвечает — оно включено и рядом?")))
            }
        }, CONNECT_TIMEOUT_MS)
    }

    fun disconnect(id: String) {
        conns[id]?.let { closeConn(it); emit("bluetooth:disconnected", JSONObject().put("device", id)) }
    }

    private fun closeConn(c: Conn) {
        if (conns[c.id] === c) conns.remove(c.id)
        c.queue.forEach { op -> op.done(Result.failure(BtException("соединение разорвано"))) }
        c.queue.clear()
        c.current?.let { op -> op.timeout?.let(main::removeCallbacks); op.done(Result.failure(BtException("соединение разорвано"))) }
        c.current = null
        c.gatt?.let { g -> runCatching { g.disconnect() }; runCatching { g.close() } }
        c.gatt = null
    }

    private fun servicesJson(g: BluetoothGatt) = JSONArray().apply {
        g.services.forEach { s ->
            put(JSONObject().put("uuid", BleUuids.format(s.uuid)).put("characteristics", JSONArray().apply {
                s.characteristics.forEach { c ->
                    put(JSONObject().put("uuid", BleUuids.format(c.uuid)).put("properties", JSONArray(props(c.properties))))
                }
            }))
        }
    }

    private fun props(p: Int) = buildList {
        if (p and BluetoothGattCharacteristic.PROPERTY_READ != 0) add("read")
        if (p and BluetoothGattCharacteristic.PROPERTY_WRITE != 0) add("write")
        if (p and BluetoothGattCharacteristic.PROPERTY_WRITE_NO_RESPONSE != 0) add("writeWithoutResponse")
        if (p and BluetoothGattCharacteristic.PROPERTY_NOTIFY != 0) add("notify")
        if (p and BluetoothGattCharacteristic.PROPERTY_INDICATE != 0) add("indicate")
    }

    private fun characteristic(id: String, service: String, characteristic: String): Pair<Conn, BluetoothGattCharacteristic> {
        val conn = conns[id] ?: throw BtException("устройство не подключено — сначала pit.bluetooth.connect()")
        val g = conn.gatt ?: throw BtException("устройство не подключено")
        val s = g.getService(BleUuids.parse(service)) ?: throw BtException("у устройства нет сервиса $service")
        val c = s.getCharacteristic(BleUuids.parse(characteristic)) ?: throw BtException("у сервиса нет характеристики $characteristic")
        return conn to c
    }

    private fun enqueue(conn: Conn, op: Op) {
        conn.queue.addLast(op)
        if (conn.current == null) runNext(conn)
    }

    private fun runNext(conn: Conn) {
        val op = conn.queue.removeFirstOrNull() ?: return
        conn.current = op
        val started = runCatching { op.start() }.getOrDefault(false)
        if (!started) {
            conn.current = null
            op.done(Result.failure(BtException("устройство отклонило операцию")))
            runNext(conn)
            return
        }
        op.timeout = Runnable { complete(conn, -1, null) }.also { main.postDelayed(it, OP_TIMEOUT_MS) }
    }

    private fun complete(conn: Conn, status: Int, value: ByteArray?) {
        val op = conn.current ?: return
        conn.current = null
        op.timeout?.let(main::removeCallbacks)
        op.done(
            when (status) {
                BluetoothGatt.GATT_SUCCESS -> Result.success(value)
                -1 -> Result.failure(BtException("устройство не ответило вовремя"))
                else -> Result.failure(BtException("ошибка Bluetooth (код $status)"))
            },
        )
        runNext(conn)
    }

    fun read(id: String, service: String, characteristic: String, done: (Result<String>) -> Unit) {
        val (conn, c) = characteristic(id, service, characteristic)
        enqueue(conn, Op({ conn.gatt?.readCharacteristic(c) == true }) { r -> done(r.map { BleUuids.encode(it ?: ByteArray(0)) }) })
    }

    fun write(id: String, service: String, characteristic: String, data: ByteArray, withoutResponse: Boolean, done: (Result<Boolean>) -> Unit) {
        val (conn, c) = characteristic(id, service, characteristic)
        if (data.size > 512) throw BtException("за один раз можно отправить не больше 512 байт")
        val type = if (withoutResponse) BluetoothGattCharacteristic.WRITE_TYPE_NO_RESPONSE else BluetoothGattCharacteristic.WRITE_TYPE_DEFAULT
        enqueue(conn, Op({
            val g = conn.gatt ?: return@Op false
            if (Build.VERSION.SDK_INT >= 33) {
                g.writeCharacteristic(c, data, type) == BluetoothStatusCodes.SUCCESS
            } else {
                @Suppress("DEPRECATION")
                run { c.writeType = type; c.value = data; g.writeCharacteristic(c) }
            }
        }) { r -> done(r.map { true }) })
    }

    /** Включить/выключить уведомления; в ответ — UUID характеристики в той записи, что придёт в событиях. */
    fun setNotifications(id: String, service: String, characteristic: String, enable: Boolean, done: (Result<String>) -> Unit) {
        val (conn, c) = characteristic(id, service, characteristic)
        val indicate = c.properties and BluetoothGattCharacteristic.PROPERTY_NOTIFY == 0 &&
            c.properties and BluetoothGattCharacteristic.PROPERTY_INDICATE != 0
        if (enable && c.properties and (BluetoothGattCharacteristic.PROPERTY_NOTIFY or BluetoothGattCharacteristic.PROPERTY_INDICATE) == 0) {
            throw BtException("характеристика не поддерживает уведомления")
        }
        val g = conn.gatt ?: throw BtException("устройство не подключено")
        if (!g.setCharacteristicNotification(c, enable)) throw BtException("не удалось включить уведомления")
        val name = BleUuids.format(c.uuid)
        val d = c.getDescriptor(BleUuids.CCCD) ?: return done(Result.success(name))
        val value = when {
            !enable -> BluetoothGattDescriptor.DISABLE_NOTIFICATION_VALUE
            indicate -> BluetoothGattDescriptor.ENABLE_INDICATION_VALUE
            else -> BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE
        }
        enqueue(conn, Op({
            val gg = conn.gatt ?: return@Op false
            if (Build.VERSION.SDK_INT >= 33) gg.writeDescriptor(d, value) == BluetoothStatusCodes.SUCCESS
            else @Suppress("DEPRECATION") run { d.value = value; gg.writeDescriptor(d) }
        }) { r -> done(r.map { name }) })
    }

    // ================================================================== классический Bluetooth: Serial (SPP)

    /**
     * Выбор Serial-устройства: сопряжённые сразу в списке, «Искать новые» находит устройства рядом,
     * а выбор нового запускает сопряжение (Android сам спросит PIN, обычно 1234 или 0000).
     */
    fun requestSerialDevice(done: (Result<JSONObject>) -> Unit) {
        val a = try { requireAdapter() } catch (e: BtException) { return done(Result.failure(e)) }
        val isSerial = { d: BluetoothDevice ->
            d.type == BluetoothDevice.DEVICE_TYPE_CLASSIC || d.type == BluetoothDevice.DEVICE_TYPE_DUAL || d.type == BluetoothDevice.DEVICE_TYPE_UNKNOWN
        }
        val devices = a.bondedDevices.orEmpty().filter(isSerial).sortedBy { it.name ?: "" }.toMutableList()
        val labels = ArrayList<String>(devices.map { it.address })
        val status = TextView(activity).apply { setPadding(60, 10, 60, 20); textSize = 13f }
        val list = ListView(activity)
        val adapter = object : ArrayAdapter<String>(activity, android.R.layout.simple_list_item_2, android.R.id.text1, labels) {
            override fun getView(position: Int, convertView: android.view.View?, parent: ViewGroup): android.view.View {
                val v = super.getView(position, convertView, parent)
                val d = devices[position]
                v.findViewById<TextView>(android.R.id.text1).text = d.name ?: "Без имени"
                v.findViewById<TextView>(android.R.id.text2).text =
                    d.address + if (d.bondState == BluetoothDevice.BOND_BONDED) " · сопряжено" else " · новое — нажмите для сопряжения"
                return v
            }
        }
        list.adapter = adapter
        fun hint() {
            status.text = if (devices.isEmpty()) "Нет сопряжённых устройств. Нажмите «Искать новые»." else "Выберите устройство или найдите новое."
        }
        hint()

        var finished = false
        var pairing: String? = null
        lateinit var dialog: AlertDialog
        val receiver = object : android.content.BroadcastReceiver() {
            override fun onReceive(context: Context, intent: Intent) {
                @Suppress("DEPRECATION")
                val d: BluetoothDevice? = if (Build.VERSION.SDK_INT >= 33) intent.getParcelableExtra(BluetoothDevice.EXTRA_DEVICE, BluetoothDevice::class.java)
                else intent.getParcelableExtra(BluetoothDevice.EXTRA_DEVICE)
                when (intent.action) {
                    BluetoothDevice.ACTION_FOUND -> if (d != null && isSerial(d) && devices.none { it.address == d.address }) {
                        devices.add(d); labels.add(d.address); adapter.notifyDataSetChanged()
                    }
                    BluetoothAdapter.ACTION_DISCOVERY_FINISHED -> if (pairing == null) status.text = "Поиск завершён. Нет нужного? Включите устройство и нажмите «Искать новые» ещё раз."
                    BluetoothDevice.ACTION_BOND_STATE_CHANGED -> if (d != null && d.address == pairing) {
                        when (intent.getIntExtra(BluetoothDevice.EXTRA_BOND_STATE, BluetoothDevice.BOND_NONE)) {
                            BluetoothDevice.BOND_BONDED -> select(d, dialog) { r -> if (!finished) { finished = true; done(r) } }
                            BluetoothDevice.BOND_NONE -> { pairing = null; status.text = "Не удалось сопрячь «${d.name ?: d.address}». Проверьте PIN и попробуйте снова." }
                        }
                    }
                }
            }
        }
        val filter = android.content.IntentFilter().apply {
            addAction(BluetoothDevice.ACTION_FOUND)
            addAction(BluetoothAdapter.ACTION_DISCOVERY_FINISHED)
            addAction(BluetoothDevice.ACTION_BOND_STATE_CHANGED)
        }
        if (Build.VERSION.SDK_INT >= 33) activity.registerReceiver(receiver, filter, Context.RECEIVER_NOT_EXPORTED)
        else activity.registerReceiver(receiver, filter)

        fun cleanup() {
            runCatching { a.cancelDiscovery() }
            runCatching { activity.unregisterReceiver(receiver) }
        }
        dialog = AlertDialog.Builder(activity)
            .setTitle("${state.manifest.name}: устройство Bluetooth")
            .setView(android.widget.LinearLayout(activity).apply {
                orientation = android.widget.LinearLayout.VERTICAL
                addView(status)
                addView(list)
            })
            .setNegativeButton("Отмена", null)
            .setNeutralButton("Искать новые", null)
            .create()
        dialog.setOnDismissListener {
            cleanup()
            if (!finished) { finished = true; done(Result.failure(BtException("пользователь отменил выбор"))) }
        }
        dialog.setOnShowListener {
            // «Искать новые» не закрывает окно
            dialog.getButton(AlertDialog.BUTTON_NEUTRAL).setOnClickListener {
                runCatching { a.cancelDiscovery() }
                status.text = if (a.startDiscovery()) "Ищем устройства рядом… (до 12 секунд)" else "Не удалось начать поиск. На Android 11 и старше включите геолокацию."
            }
        }
        list.setOnItemClickListener { _, _, pos, _ ->
            val d = devices[pos]
            if (d.bondState == BluetoothDevice.BOND_BONDED) {
                select(d, dialog) { r -> if (!finished) { finished = true; done(r) } }
            } else {
                runCatching { a.cancelDiscovery() }
                pairing = d.address
                status.text = "Сопряжение с «${d.name ?: d.address}»… Подтвердите на экране (PIN обычно 1234 или 0000)."
                if (!d.createBond()) { pairing = null; status.text = "Не удалось начать сопряжение" }
            }
        }
        dialog.show()
    }

    private fun select(d: BluetoothDevice, dialog: AlertDialog, done: (Result<JSONObject>) -> Unit) {
        val dev = AppState.Device(d.address, d.name ?: "Без имени", TYPE_SERIAL)
        state.approveDevice(dev)
        done(Result.success(deviceJson(dev)))
        dialog.dismiss()
    }

    private class Serial(val socket: BluetoothSocket) {
        val writer = Executors.newSingleThreadExecutor()
    }

    private val serials = mutableMapOf<String, Serial>()

    fun serialConnect(id: String, done: (Result<Boolean>) -> Unit) {
        if (!state.isApproved(id, TYPE_SERIAL)) return done(Result.failure(BtException("устройство не выбрано пользователем — сначала pit.bluetooth.serial.requestDevice()")))
        if (id in serials) return done(Result.success(true))
        val a = try { requireAdapter() } catch (e: BtException) { return done(Result.failure(e)) }
        val dev = runCatching { a.getRemoteDevice(id.uppercase()) }.getOrNull() ?: return done(Result.failure(BtException("неверный адрес устройства")))
        io.execute {
            runCatching { a.cancelDiscovery() }
            val socket = try {
                dev.createRfcommSocketToServiceRecord(BleUuids.SPP).also { it.connect() }
            } catch (e: IOException) {
                main.post { done(Result.failure(BtException("не удалось подключиться: устройство включено и сопряжено?"))) }
                return@execute
            }
            val s = Serial(socket)
            main.post {
                serials[id] = s
                done(Result.success(true))
            }
            // чтение в отдельном потоке, пока соединение открыто
            val buf = ByteArray(1024)
            try {
                val input = socket.inputStream
                while (true) {
                    val n = input.read(buf)
                    if (n < 0) break
                    val chunk = buf.copyOf(n)
                    main.post { emit("bluetooth:serial", JSONObject().put("device", id).put("value", BleUuids.encode(chunk))) }
                }
            } catch (e: IOException) {
                // соединение закрыто
            }
            main.post {
                if (serials[id] === s) {
                    serials.remove(id)
                    closeSerial(s)
                    emit("bluetooth:disconnected", JSONObject().put("device", id))
                }
            }
        }
    }

    fun serialWrite(id: String, data: ByteArray, done: (Result<Boolean>) -> Unit) {
        val s = serials[id] ?: throw BtException("устройство не подключено — сначала pit.bluetooth.serial.connect()")
        s.writer.execute {
            val r = runCatching { s.socket.outputStream.write(data); s.socket.outputStream.flush(); true }
                .recoverCatching { throw BtException("не удалось отправить: соединение разорвано") }
            main.post { done(r) }
        }
    }

    fun serialDisconnect(id: String) {
        serials.remove(id)?.let { closeSerial(it); emit("bluetooth:disconnected", JSONObject().put("device", id)) }
    }

    private fun closeSerial(s: Serial) {
        runCatching { s.socket.close() }
        s.writer.shutdown()
    }

    /** Приложение закрывается — отключаемся от всего. */
    fun closeAll() {
        adapter?.bluetoothLeScanner?.let { stopScan(it) }
        conns.values.toList().forEach { closeConn(it) }
        serials.values.toList().forEach { closeSerial(it) }
        serials.clear()
        io.shutdownNow()
    }

    companion object {
        const val TYPE_BLE = "ble"
        const val TYPE_SERIAL = "serial"
        private const val SCAN_TIME_MS = 20_000L
        private const val CONNECT_TIMEOUT_MS = 15_000L
        private const val OP_TIMEOUT_MS = 10_000L
    }
}
