package com.robutpit.roachrace

import android.Manifest
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.robutpit.roachrace.bluetooth.BtRaceLink
import com.robutpit.roachrace.bluetooth.LinkState
import com.robutpit.roachrace.bluetooth.RaceProtocol
import com.robutpit.roachrace.data.SaveRepository
import com.robutpit.roachrace.data.SaveState
import com.robutpit.roachrace.engine.RaceEngine
import com.robutpit.roachrace.engine.TrainGymEngine
import com.robutpit.roachrace.model.*
import com.robutpit.roachrace.sensors.MicListener
import com.robutpit.roachrace.sensors.MotionListener
import com.robutpit.roachrace.ui.*
import com.robutpit.roachrace.ui.theme.*
import kotlin.random.Random

class MainActivity : ComponentActivity() {

    private lateinit var micPermissionLauncher: androidx.activity.result.ActivityResultLauncher<String>
    private lateinit var btPermissionLauncher: androidx.activity.result.ActivityResultLauncher<Array<String>>
    private lateinit var enableBtLauncher: androidx.activity.result.ActivityResultLauncher<android.content.Intent>

    private var onMicGranted: (() -> Unit)? = null
    private var onBtPermsGranted: (() -> Unit)? = null
    private var onBtEnabled: (() -> Unit)? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        micPermissionLauncher = registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
            if (granted) onMicGranted?.invoke()
        }
        btPermissionLauncher = registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { result ->
            if (result.values.all { it }) onBtPermsGranted?.invoke()
        }
        enableBtLauncher = registerForActivityResult(ActivityResultContracts.StartActivityForResult()) {
            onBtEnabled?.invoke()
        }

        setContent {
            RoachRaceTheme {
                Surface(color = BgDeep) {
                    AppRoot(
                        requestMicPermission = { onGranted ->
                            onMicGranted = onGranted
                            micPermissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
                        },
                        requestBtPermissions = { onGranted ->
                            onBtPermsGranted = onGranted
                            val perms = if (Build.VERSION.SDK_INT >= 31) {
                                arrayOf(Manifest.permission.BLUETOOTH_CONNECT, Manifest.permission.BLUETOOTH_SCAN)
                            } else {
                                arrayOf(Manifest.permission.ACCESS_FINE_LOCATION)
                            }
                            btPermissionLauncher.launch(perms)
                        },
                        requestEnableBluetooth = { onEnabled ->
                            onBtEnabled = onEnabled
                            enableBtLauncher.launch(android.content.Intent(BluetoothAdapter.ACTION_REQUEST_ENABLE))
                        },
                    )
                }
            }
        }
    }
}

@Composable
fun AppRoot(
    requestMicPermission: (onGranted: () -> Unit) -> Unit,
    requestBtPermissions: (onGranted: () -> Unit) -> Unit,
    requestEnableBluetooth: (onEnabled: () -> Unit) -> Unit,
) {
    val context = LocalContext.current
    val repo = remember { SaveRepository(context) }
    var save by remember { mutableStateOf(repo.load()) }
    fun persist(newSave: SaveState) {
        save = newSave
        repo.save(newSave)
    }

    var screen by remember { mutableStateOf(if (save.breed == null) Screen.SELECT else Screen.TRAIN) }
    var engine by remember { mutableStateOf<RaceEngine?>(null) }
    var isMultiplayer by remember { mutableStateOf(false) }
    var mpRole by remember { mutableStateOf(MpRole.NONE) }
    var remoteHello by remember { mutableStateOf<RaceProtocol.Hello?>(null) }
    var helloSent by remember { mutableStateOf(false) }

    val btLink = remember { BtRaceLink(context.applicationContext) }
    var micActive by remember { mutableStateOf(false) }
    var micLevel by remember { mutableStateOf(0f) }
    var micStatus by remember { mutableStateOf("выкл") }
    var motionActive by remember { mutableStateOf(false) }
    var motionLevel by remember { mutableStateOf(0f) }
    var motionStatus by remember { mutableStateOf("выкл") }
    var hardcore by remember { mutableStateOf(false) }

    fun spookFromLocalSensor(sourceLabel: String) {
        val eng = engine ?: return
        if (!isMultiplayer) {
            eng.hardcore = hardcore
            eng.spookRandomRacer(sourceLabel)
        } else if (mpRole == MpRole.HOST) {
            eng.hardcore = hardcore
            eng.spookRandomRacer(sourceLabel, targetIdOverride = 1)
        } else if (mpRole == MpRole.JOIN) {
            btLink.send(RaceProtocol.spook(sourceLabel))
        }
    }

    val micListener = remember {
        MicListener(
            context = context,
            onLevel = { micLevel = it },
            onPeak = { spookFromLocalSensor("Ты (крик)") },
        )
    }
    val motionListener = remember {
        MotionListener(
            context = context,
            onLevel = { motionLevel = it },
            onPeak = { spookFromLocalSensor("Ты (стук)") },
        )
    }

    val gymEngine = remember {
        TrainGymEngine().apply {
            setCallbacks(
                onFeed = {
                    val newStamina = if (save.levels.stamina < 10 && Random.nextFloat() < 0.7f) save.levels.stamina + 1 else save.levels.stamina
                    persist(save.copy(satiety = (save.satiety + 25).coerceIn(0, 100), levels = save.levels.copy(stamina = newStamina)))
                },
                onTrain = {
                    val newSpeed = if (save.levels.speed < 10) save.levels.speed + 1 else save.levels.speed
                    val newStress = if (save.levels.stress < 10 && Random.nextFloat() < 0.4f) save.levels.stress + 1 else save.levels.stress
                    persist(save.copy(satiety = (save.satiety - 20).coerceIn(0, 100), levels = save.levels.copy(speed = newSpeed, stress = newStress)))
                },
            )
        }
    }
    LaunchedEffect(screen) {
        if (screen != Screen.TRAIN) return@LaunchedEffect
        var last = withFrameNanos { it }
        while (true) {
            val now = withFrameNanos { it }
            val dt = ((now - last) / 1_000_000_000.0).toFloat().coerceAtMost(0.05f)
            last = now
            gymEngine.step(dt)
        }
    }

    DisposableEffect(Unit) {
        onDispose {
            micListener.stop()
            motionListener.stop()
            btLink.close()
        }
    }

    fun stopRaceSensors() {
        micListener.stop(); micActive = false; micStatus = "выкл"
        motionListener.stop(); motionActive = false; motionStatus = "выкл"
    }

    fun buildSoloEngine(track: Track): RaceEngine {
        val playerBreed = save.breed ?: Breed.BLACK
        val player = Racer("Ты", isPlayer = true, isRemote = false, breed = playerBreed, colorLong = colorById(save.colorId).colorLong, levels = save.levels)
        val botNames = listOf("Сосед по опенспейсу", "Бухгалтерия", "HR-чемпион")
        val usedColors = ROACH_COLORS.filter { it.id != save.colorId }
        val bots = (0 until 3).map { i ->
            val peak = listOf(2, 5, 8)[i % 3]
            Racer(
                botNames[i], isPlayer = false, isRemote = false,
                breed = Breed.random(), colorLong = usedColors[i % usedColors.size].colorLong,
                levels = Levels(Random.nextInt(0, peak + 1), Random.nextInt(0, peak + 1), Random.nextInt(0, peak + 1)),
            )
        }
        return RaceEngine(track, listOf(player) + bots)
    }

    fun handleIncomingLine(line: String) {
        RaceProtocol.parseHello(line)?.let { hello -> remoteHello = hello; return }
        RaceProtocol.parseTrack(line)?.let { trackId ->
            if (mpRole == MpRole.JOIN) persist(save.copy(trackId = trackId))
            return
        }
        if (line == RaceProtocol.start() && mpRole == MpRole.JOIN) {
            val hostHello = remoteHello
            val track = trackById(save.trackId ?: "table")
            val hostRacer = Racer(
                hostHello?.name ?: "Хост", isPlayer = false, isRemote = true,
                breed = hostHello?.breed ?: Breed.BLACK, colorLong = hostHello?.colorLong ?: 0xFFB5541EL,
                levels = hostHello?.levels ?: Levels(),
            )
            val meRacer = Racer(
                "Ты", isPlayer = true, isRemote = true,
                breed = save.breed ?: Breed.BLACK, colorLong = colorById(save.colorId).colorLong, levels = save.levels,
            )
            val eng = RaceEngine(track, listOf(hostRacer, meRacer))
            eng.start()
            engine = eng
            isMultiplayer = true
            screen = Screen.RACE
            return
        }
        RaceProtocol.parseState(line)?.let { entries ->
            val eng = engine ?: return
            entries.forEach { e -> eng.applyRemoteSnapshot(e.index, e.progress, e.wobble, e.spook, e.finished) }
            return
        }
        RaceProtocol.parseSpook(line)?.let { label ->
            if (mpRole == MpRole.HOST) {
                engine?.spookRandomRacer("Соперник: $label", targetIdOverride = 0)
            }
            return
        }
    }

    btLink.onLine = { line -> handleIncomingLine(line) }

    LaunchedEffect(btLink.state.value) {
        val st = btLink.state.value
        if (st is LinkState.Connected && !helloSent) {
            helloSent = true
            btLink.send(RaceProtocol.hello("Игрок", save.breed ?: Breed.BLACK, colorById(save.colorId).colorLong, save.levels))
        }
        if (st !is LinkState.Connected) helloSent = false
    }

    // Main simulation loop: advances the active race engine every frame and,
    // when hosting a Bluetooth race, streams a state snapshot to the joined
    // phone a few times a second.
    LaunchedEffect(engine) {
        val eng = engine ?: return@LaunchedEffect
        var frame = 0
        var last = withFrameNanos { it }
        while (true) {
            val now = withFrameNanos { it }
            val dt = ((now - last) / 1_000_000_000.0).toFloat().coerceAtMost(0.05f)
            last = now
            eng.step(dt)
            frame++
            if (isMultiplayer && mpRole == MpRole.HOST && frame % 3 == 0) {
                btLink.send(RaceProtocol.state(eng))
            }
            if (eng.done.value) {
                if (isMultiplayer && mpRole == MpRole.HOST) btLink.send(RaceProtocol.state(eng))
                screen = Screen.RESULTS
                break
            }
        }
    }

    if (screen == Screen.RACE && engine != null) {
        val eng = engine!!
        RaceScreen(
            engine = eng,
            onStart = { eng.start() },
            onBackToTrack = {
                stopRaceSensors()
                if (isMultiplayer) btLink.close()
                screen = Screen.TRACK
            },
            micActive = micActive,
            micLevel = micLevel,
            micStatus = micStatus,
            onToggleMic = {
                if (micActive) {
                    micListener.stop(); micActive = false; micStatus = "выкл"
                } else if (micListener.hasPermission()) {
                    micActive = micListener.start(); micStatus = if (micActive) "слушаю" else "ошибка"
                } else {
                    requestMicPermission {
                        micActive = micListener.start(); micStatus = if (micActive) "слушаю" else "ошибка"
                    }
                }
            },
            motionActive = motionActive,
            motionLevel = motionLevel,
            motionStatus = motionStatus,
            onToggleMotion = {
                if (motionActive) {
                    motionListener.stop(); motionActive = false; motionStatus = "выкл"
                } else if (motionListener.hasSensor()) {
                    motionActive = motionListener.start(); motionStatus = if (motionActive) "слушаю" else "ошибка"
                } else {
                    motionStatus = "нет датчика"
                }
            },
            hardcore = hardcore,
            onHardcoreChange = { hardcore = it; eng.hardcore = it },
            multiplayerHint = if (isMultiplayer) {
                if (mpRole == MpRole.HOST) "Bluetooth: ты хост, гонка синхронизируется на оба телефона" else "Bluetooth: ты подключился, поле зеркалится с телефона хоста"
            } else null,
        )
        return
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
    ) {
        Text("🪳 Тараканьи бега", fontWeight = FontWeight.Bold, fontSize = 22.sp, color = TextMain)
        Text("Порода · тренировка · трассы · звук и вибрация · Bluetooth", fontSize = 12.sp, color = TextDim)

        StepNav(
            current = screen,
            canGoTrain = save.breed != null,
            canGoTrack = save.breed != null,
            canGoRace = save.breed != null && save.trackId != null,
            canGoResults = engine?.done?.value == true,
            onNav = { target ->
                if (target != Screen.RACE) stopRaceSensors()
                screen = target
            },
        )

        if (save.breed != null) {
            Spacer(Modifier.height(4.dp))
            RoachBadge(save)
            Spacer(Modifier.height(10.dp))
        }

        when (screen) {
            Screen.SELECT -> SelectScreen(
                save = save,
                onBreed = { persist(save.copy(breed = it)) },
                onColor = { persist(save.copy(colorId = it)) },
                onConfirm = { screen = Screen.TRAIN },
            )
            Screen.TRAIN -> TrainGymScreen(
                save = save,
                engine = gymEngine,
                onResetRoach = {
                    repo.reset()
                    save = repo.load()
                    engine = null
                    screen = Screen.SELECT
                },
                onNext = { screen = Screen.TRACK },
            )
            Screen.TRACK -> TrackScreen(
                selectedTrackId = save.trackId,
                onPick = { persist(save.copy(trackId = it)) },
                onSolo = {
                    val track = trackById(save.trackId ?: return@TrackScreen)
                    isMultiplayer = false
                    mpRole = MpRole.NONE
                    engine = buildSoloEngine(track)
                    screen = Screen.RACE
                },
                onMultiplayer = {
                    mpRole = MpRole.NONE
                    remoteHello = null
                    screen = Screen.MULTIPLAYER
                },
            )
            Screen.MULTIPLAYER -> MultiplayerScreen(
                role = mpRole,
                state = btLink.state.value,
                bondedDevices = btLink.bondedDevices(),
                discoveredDevices = btLink.discoveredDevices,
                onPickHost = {
                    requestBtPermissions {
                        requestEnableBluetooth {
                            mpRole = MpRole.HOST
                            btLink.startHosting()
                        }
                    }
                },
                onPickJoin = {
                    requestBtPermissions {
                        requestEnableBluetooth {
                            mpRole = MpRole.JOIN
                        }
                    }
                },
                onDeviceSelected = { device -> btLink.connectTo(device) },
                onRescan = { btLink.startDiscovery() },
                onProceed = {
                    val hello = remoteHello ?: return@MultiplayerScreen
                    val track = trackById(save.trackId ?: "table")
                    val hostRacer = Racer(
                        "Ты", isPlayer = true, isRemote = false,
                        breed = save.breed ?: Breed.BLACK, colorLong = colorById(save.colorId).colorLong, levels = save.levels,
                    )
                    val joinRacer = Racer(
                        hello.name, isPlayer = false, isRemote = false,
                        breed = hello.breed, colorLong = hello.colorLong, levels = hello.levels,
                    )
                    val eng = RaceEngine(track, listOf(hostRacer, joinRacer))
                    isMultiplayer = true
                    engine = eng
                    btLink.send(RaceProtocol.track(track.id))
                    btLink.send(RaceProtocol.start())
                    eng.start()
                    screen = Screen.RACE
                },
                onRetry = {
                    btLink.close()
                    remoteHello = null
                    mpRole = MpRole.NONE
                },
                onBack = {
                    btLink.close()
                    mpRole = MpRole.NONE
                    screen = Screen.TRACK
                },
            )
            Screen.RACE -> Unit
            Screen.RESULTS -> engine?.let { eng ->
                val ranking = eng.racers.sortedBy { it.finishOrder ?: Int.MAX_VALUE }
                val rows = ranking.mapIndexed { i, r ->
                    Triple(i + 1, (if (r.isPlayer) "${r.name} (ты)" else r.name), r.finishTimeSec?.let { "%.2f с".format(it) } ?: "—")
                }
                val playerPlace = ranking.indexOfFirst { it.isPlayer } + 1
                ResultsScreen(
                    rows = rows,
                    playerPlace = playerPlace,
                    total = ranking.size,
                    onAnotherTrack = {
                        stopRaceSensors()
                        if (isMultiplayer) btLink.close()
                        screen = Screen.TRACK
                    },
                    onTrainMore = {
                        stopRaceSensors()
                        if (isMultiplayer) btLink.close()
                        screen = Screen.TRAIN
                    },
                )
            }
        }

        Spacer(Modifier.height(16.dp))
        Text(
            "Прототип механик, собранный как настоящее Android-приложение. Bluetooth-режим вдвоём (общее поле на обоих экранах) " +
                "реализован через классический RFCOMM и проверен по коду, но не тестировался на живой паре телефонов — " +
                "первый запуск считайте бета-тестом. Режим «сложить телефоны в одно большое поле» пока не реализован.",
            fontSize = 10.sp, color = TextDim, lineHeight = 14.sp,
        )
    }
}
