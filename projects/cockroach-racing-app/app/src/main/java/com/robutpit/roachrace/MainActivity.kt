package com.robutpit.roachrace

import android.Manifest
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
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
    private lateinit var discoverableLauncher: androidx.activity.result.ActivityResultLauncher<android.content.Intent>

    private var onMicGranted: (() -> Unit)? = null
    private var onBtPermsGranted: (() -> Unit)? = null
    private var onBtEnabled: (() -> Unit)? = null
    private var onDiscoverableDone: (() -> Unit)? = null

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
        // The system discoverability dialog always returns a result (either the
        // chosen duration or RESULT_CANCELED if the user dismissed it) — either
        // way we move on, since RFCOMM itself doesn't strictly require it when
        // the phones are already paired, only when relying on live scanning.
        discoverableLauncher = registerForActivityResult(ActivityResultContracts.StartActivityForResult()) {
            onDiscoverableDone?.invoke()
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
                                arrayOf(Manifest.permission.BLUETOOTH_CONNECT, Manifest.permission.BLUETOOTH_SCAN, Manifest.permission.BLUETOOTH_ADVERTISE)
                            } else {
                                arrayOf(Manifest.permission.ACCESS_FINE_LOCATION)
                            }
                            btPermissionLauncher.launch(perms)
                        },
                        requestEnableBluetooth = { onEnabled ->
                            onBtEnabled = onEnabled
                            enableBtLauncher.launch(android.content.Intent(BluetoothAdapter.ACTION_REQUEST_ENABLE))
                        },
                        requestDiscoverable = { onDone ->
                            onDiscoverableDone = onDone
                            val intent = android.content.Intent(BluetoothAdapter.ACTION_REQUEST_DISCOVERABLE)
                                .putExtra(BluetoothAdapter.EXTRA_DISCOVERABLE_DURATION, 300)
                            discoverableLauncher.launch(intent)
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
    requestDiscoverable: (onDone: () -> Unit) -> Unit,
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

    // Host-side lobby bookkeeping: each joiner's HELLO as it arrives, keyed by
    // their (stable, gap-tolerant) connection id.
    var remoteHellos by remember { mutableStateOf<Map<Int, RaceProtocol.Hello>>(emptyMap()) }
    // Set once the race actually starts, mapping a joiner's connection id to
    // the *final* contiguous racer index it was assigned (these can differ if
    // someone connected then left before the host pressed start).
    var peerIdToRacerIndex by remember { mutableStateOf<Map<Int, Int>>(emptyMap()) }

    // Join-side: who am I in the roster, and what does the whole roster look like.
    var myAssignedIndex by remember { mutableStateOf<Int?>(null) }
    var remoteRoster by remember { mutableStateOf<List<RaceProtocol.Hello>>(emptyList()) }
    var helloSent by remember { mutableStateOf(false) }

    // Tournament mode: several heats in a row (Bluetooth caps one heat at
    // MAX_PEERS+1 players), placements accumulate into a shared points table.
    var tournamentMode by remember { mutableStateOf(false) }
    val tournamentBoard = remember { mutableStateListOf<TournamentEntry>() }

    // "Combined field" mode: host picks it in the lobby, joiners learn it from
    // the START message. mySegmentIndex/totalSegments describe which slice of
    // the track this phone renders (host is always segment 0).
    var stitchedModeChoice by remember { mutableStateOf(false) }
    var isStitchedRace by remember { mutableStateOf(false) }
    var mySegmentIndex by remember { mutableStateOf(0) }
    var totalSegments by remember { mutableStateOf(1) }

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
        eng.hardcore = hardcore
        if (!isMultiplayer) {
            eng.spookRandomRacer(sourceLabel, sourceIndex = 0)
        } else if (mpRole == MpRole.HOST) {
            eng.spookRandomRacer(sourceLabel, sourceIndex = 0)
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
        val player = Racer(save.displayName(), isPlayer = true, isRemote = false, breed = playerBreed, colorLong = colorById(save.colorId).colorLong, levels = save.levels)
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

    fun handleIncomingLine(peerId: Int, line: String) {
        RaceProtocol.parseHello(line)?.let { hello ->
            if (mpRole == MpRole.HOST) remoteHellos = remoteHellos + (peerId to hello)
            return
        }
        RaceProtocol.parseWelcome(line)?.let { idx ->
            if (mpRole == MpRole.JOIN) myAssignedIndex = idx
            return
        }
        RaceProtocol.parseRoster(line)?.let { roster ->
            if (mpRole == MpRole.JOIN) remoteRoster = roster
            return
        }
        RaceProtocol.parseTrack(line)?.let { trackId ->
            if (mpRole == MpRole.JOIN) persist(save.copy(trackId = trackId))
            return
        }
        RaceProtocol.parseStart(line)?.let { stitched ->
            if (mpRole != MpRole.JOIN) return
            val myIdx = myAssignedIndex
            if (myIdx == null || remoteRoster.isEmpty()) return
            val track = trackById(save.trackId ?: "table")
            val racers = remoteRoster.mapIndexed { i, h ->
                Racer(h.name, isPlayer = (i == myIdx), isRemote = true, breed = h.breed, colorLong = h.colorLong, levels = h.levels)
            }
            val eng = RaceEngine(track, racers)
            eng.start()
            engine = eng
            isMultiplayer = true
            isStitchedRace = stitched
            mySegmentIndex = myIdx
            totalSegments = remoteRoster.size
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
                val racerIndex = peerIdToRacerIndex[peerId] ?: return
                engine?.spookRandomRacer("Игрок $racerIndex: $label", sourceIndex = racerIndex)
            }
            return
        }
    }

    btLink.onLine = { peerId, line -> handleIncomingLine(peerId, line) }

    // Joiner sends its own HELLO once connected, so the host can add it to
    // the roster. The host doesn't need this — it builds its own racer entry
    // from local `save` directly, no round trip needed.
    LaunchedEffect(btLink.state.value, mpRole) {
        val st = btLink.state.value
        if (mpRole == MpRole.JOIN && st is LinkState.Connected && !helloSent) {
            helloSent = true
            btLink.send(RaceProtocol.hello(save.displayName(), save.breed ?: Breed.BLACK, colorById(save.colorId).colorLong, save.levels))
        }
        if (st !is LinkState.Connected) helloSent = false
    }

    // Main simulation loop: advances the active race engine every frame and,
    // when hosting a Bluetooth race, streams a state snapshot to every
    // connected phone a few times a second.
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
                btLink.sendToAll(RaceProtocol.state(eng))
            }
            if (eng.done.value) {
                if (isMultiplayer && mpRole == MpRole.HOST) {
                    btLink.sendToAll(RaceProtocol.state(eng))
                    if (tournamentMode) {
                        val ranking = eng.racers.sortedBy { it.finishOrder ?: Int.MAX_VALUE }
                        ranking.forEachIndexed { i, r ->
                            val place = i + 1
                            val existing = tournamentBoard.find { it.name == r.name }
                            if (existing != null) {
                                tournamentBoard.remove(existing)
                                tournamentBoard.add(
                                    existing.copy(
                                        points = existing.points + pointsForPlace(place),
                                        heats = existing.heats + 1,
                                        bestPlace = minOf(existing.bestPlace, place),
                                    ),
                                )
                            } else {
                                tournamentBoard.add(TournamentEntry(r.name, pointsForPlace(place), 1, place))
                            }
                        }
                    }
                }
                screen = Screen.RESULTS
                break
            }
        }
    }

    if (screen == Screen.RACE && engine != null) {
        val eng = engine!!
        val onBackToTrack: () -> Unit = {
            stopRaceSensors()
            if (isMultiplayer) btLink.close()
            screen = Screen.TRACK
        }
        val onToggleMic: () -> Unit = {
            if (micActive) {
                micListener.stop(); micActive = false; micStatus = "выкл"
            } else if (micListener.hasPermission()) {
                micActive = micListener.start(); micStatus = if (micActive) "слушаю" else "ошибка"
            } else {
                requestMicPermission {
                    micActive = micListener.start(); micStatus = if (micActive) "слушаю" else "ошибка"
                }
            }
        }
        val onToggleMotion: () -> Unit = {
            if (motionActive) {
                motionListener.stop(); motionActive = false; motionStatus = "выкл"
            } else if (motionListener.hasSensor()) {
                motionActive = motionListener.start(); motionStatus = if (motionActive) "слушаю" else "ошибка"
            } else {
                motionStatus = "нет датчика"
            }
        }
        val onHardcoreChange: (Boolean) -> Unit = { hardcore = it; eng.hardcore = it }

        if (isMultiplayer && isStitchedRace) {
            StitchedRaceScreen(
                engine = eng,
                mySegmentIndex = mySegmentIndex,
                totalSegments = totalSegments,
                onStart = { eng.start() },
                onBackToTrack = onBackToTrack,
                micActive = micActive, micLevel = micLevel, micStatus = micStatus, onToggleMic = onToggleMic,
                motionActive = motionActive, motionLevel = motionLevel, motionStatus = motionStatus, onToggleMotion = onToggleMotion,
                hardcore = hardcore, onHardcoreChange = onHardcoreChange,
            )
        } else {
            RaceScreen(
                engine = eng,
                onStart = { eng.start() },
                onBackToTrack = onBackToTrack,
                micActive = micActive, micLevel = micLevel, micStatus = micStatus, onToggleMic = onToggleMic,
                motionActive = motionActive, motionLevel = motionLevel, motionStatus = motionStatus, onToggleMotion = onToggleMotion,
                hardcore = hardcore, onHardcoreChange = onHardcoreChange,
                multiplayerHint = if (isMultiplayer) {
                    if (mpRole == MpRole.HOST) "Bluetooth: ты хост, гонка синхронизируется на все телефоны (${eng.racers.size} игроков)" else "Bluetooth: ты подключился, поле зеркалится с телефона хоста"
                } else null,
            )
        }
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
                onName = { persist(save.copy(name = it)) },
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
                    isStitchedRace = false
                    mpRole = MpRole.NONE
                    engine = buildSoloEngine(track)
                    screen = Screen.RACE
                },
                onMultiplayer = {
                    mpRole = MpRole.NONE
                    remoteHellos = emptyMap()
                    peerIdToRacerIndex = emptyMap()
                    myAssignedIndex = null
                    remoteRoster = emptyList()
                    stitchedModeChoice = false
                    screen = Screen.MULTIPLAYER
                },
            )
            Screen.MULTIPLAYER -> MultiplayerScreen(
                role = mpRole,
                state = btLink.state.value,
                hostPeerNames = btLink.hostPeers.map { it.displayName },
                bondedDevices = btLink.bondedDevices(),
                discoveredDevices = btLink.discoveredDevices,
                onPickHost = {
                    requestBtPermissions {
                        requestEnableBluetooth {
                            requestDiscoverable {
                                mpRole = MpRole.HOST
                                btLink.startHosting()
                            }
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
                stitchedMode = stitchedModeChoice,
                onStitchedModeChange = { stitchedModeChoice = it },
                tournamentMode = tournamentMode,
                onTournamentModeChange = { tournamentMode = it },
                onStartRace = {
                    btLink.stopAcceptingNewPeers()
                    val orderedPeers = btLink.hostPeers.filter { remoteHellos.containsKey(it.id) }.sortedBy { it.id }
                    val track = trackById(save.trackId ?: "table")
                    val hostHello = RaceProtocol.Hello(save.displayName(), save.breed ?: Breed.BLACK, colorById(save.colorId).colorLong, save.levels)
                    val fullRoster = listOf(hostHello) + orderedPeers.map { remoteHellos.getValue(it.id) }
                    val racers = fullRoster.mapIndexed { i, h ->
                        Racer(h.name, isPlayer = (i == 0), isRemote = false, breed = h.breed, colorLong = h.colorLong, levels = h.levels)
                    }
                    peerIdToRacerIndex = orderedPeers.mapIndexed { i, peer -> peer.id to (i + 1) }.toMap()
                    orderedPeers.forEachIndexed { i, peer -> btLink.sendToPeer(peer.id, RaceProtocol.welcome(i + 1)) }
                    btLink.sendToAll(RaceProtocol.roster(fullRoster))
                    btLink.sendToAll(RaceProtocol.track(track.id))
                    btLink.sendToAll(RaceProtocol.start(stitchedModeChoice))
                    val eng = RaceEngine(track, racers)
                    isMultiplayer = true
                    isStitchedRace = stitchedModeChoice
                    mySegmentIndex = 0
                    totalSegments = racers.size
                    engine = eng
                    eng.start()
                    screen = Screen.RACE
                },
                onRetry = {
                    btLink.close()
                    remoteHellos = emptyMap()
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
                    showTournamentButton = isMultiplayer && tournamentMode,
                    onShowTournament = { screen = Screen.TOURNAMENT },
                )
            }
            Screen.TOURNAMENT -> TournamentScreen(
                entries = tournamentBoard,
                onNextHeat = {
                    stopRaceSensors()
                    btLink.close()
                    mpRole = MpRole.NONE
                    screen = Screen.TRACK
                },
                onFinish = {
                    stopRaceSensors()
                    btLink.close()
                    mpRole = MpRole.NONE
                    tournamentMode = false
                    tournamentBoard.clear()
                    screen = Screen.TRACK
                },
            )
        }

        Spacer(Modifier.height(16.dp))
        Text(
            "Прототип механик, собранный как настоящее Android-приложение. Bluetooth-турнир до " +
                "${com.robutpit.roachrace.bluetooth.MAX_PEERS + 1} игроков реализован через классический RFCOMM, в двух режимах: " +
                "общее поле на всех экранах сразу, и «сложить телефоны в ряд» — у каждого свой участок трассы.",
            fontSize = 10.sp, color = TextDim, lineHeight = 14.sp,
        )
    }
}
