package com.robutpit.zamri.ui

import android.app.Application
import androidx.camera.core.ImageProxy
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.robutpit.zamri.ZamriApp
import com.robutpit.zamri.audio.Cue
import com.robutpit.zamri.audio.SoundCues
import com.robutpit.zamri.data.GameRepository
import com.robutpit.zamri.data.GameSettings
import com.robutpit.zamri.data.SettingsStore
import com.robutpit.zamri.data.db.ViolationSide
import com.robutpit.zamri.motion.ImageUtils
import com.robutpit.zamri.motion.MotionDetector
import com.robutpit.zamri.motion.SectorTrigger
import com.robutpit.zamri.tts.VoiceAnnouncer
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlin.random.Random

class GameViewModel(
    application: Application,
    private val repository: GameRepository,
    private val settingsStore: SettingsStore
) : AndroidViewModel(application) {

    val settings: StateFlow<GameSettings> = settingsStore.settings.stateIn(
        viewModelScope, SharingStarted.WhileSubscribed(5000), GameSettings()
    )

    private val _phase = MutableStateFlow<GamePhase>(GamePhase.Idle)
    val phase: StateFlow<GamePhase> = _phase.asStateFlow()

    private val _lastViolation = MutableStateFlow<ViolationUiEvent?>(null)
    val lastViolation: StateFlow<ViolationUiEvent?> = _lastViolation.asStateFlow()

    private val voice = VoiceAnnouncer(application)
    private val soundCues = SoundCues(application)

    private var currentRound = 0
    private var sessionViolationCount = 0
    private val violationLock = Mutex()
    private var processingViolation = false
    private var gameLoopJob: Job? = null
    private var finishRequested = false

    /**
     * Owned here so the phase logic can arm/disarm it directly; the camera
     * screen only needs to bind it as an [androidx.camera.core.ImageAnalysis]
     * use case and keep it fed with frames.
     */
    val motionDetector = MotionDetector(
        sectorCount = settings.value.sectorCount,
        sensitivityPercent = settings.value.sensitivityPercent
    ) { triggers, image -> onMotionTriggers(triggers, image) }

    init {
        viewModelScope.launch {
            settings.collect { s ->
                motionDetector.updateSectorCount(s.sectorCount)
                motionDetector.updateSensitivity(s.sensitivityPercent)
                voice.volume = s.volumePercent / 100f
                soundCues.volume = s.volumePercent / 100f
                soundCues.applyStreamVolume(s.volumePercent / 100f)
            }
        }
    }

    fun updateSettings(newSettings: GameSettings) {
        viewModelScope.launch { settingsStore.update(newSettings) }
    }

    fun startGame() {
        if (gameLoopJob?.isActive == true) return
        finishRequested = false
        currentRound = 0
        sessionViolationCount = 0
        gameLoopJob = viewModelScope.launch { runGameLoop() }
    }

    fun finishGame() {
        finishRequested = true
    }

    fun returnToIdle() {
        gameLoopJob?.cancel()
        motionDetector.armed = false
        _phase.value = GamePhase.Idle
        _lastViolation.value = null
    }

    private suspend fun runGameLoop() {
        val cfg = settings.value
        _phase.value = GamePhase.Countdown(3)
        for (secondsLeft in 3 downTo 1) {
            _phase.value = GamePhase.Countdown(secondsLeft)
            delay(1000)
        }

        val totalGameSec = cfg.roundDurationSec
        var elapsedSec = 0

        while (!finishRequested && elapsedSec < totalGameSec) {
            currentRound++

            // --- Green light: movement allowed, detector paused to save battery ---
            motionDetector.armed = false
            val greenSec = randomGreenDuration(cfg)
            if (cfg.soundEnabled) {
                soundCues.play(Cue.GREEN_START)
                voice.speakPhase(isGreen = true)
            }
            var greenLeft = greenSec
            while (!finishRequested && greenLeft > 0 && elapsedSec < totalGameSec) {
                _phase.value = GamePhase.Green(currentRound, elapsedSec, totalGameSec)
                delay(1000)
                greenLeft--
                elapsedSec++
            }
            if (finishRequested || elapsedSec >= totalGameSec) break

            // --- Red light: doll turns around, detector arms for the freeze window ---
            motionDetector.resetBaseline()
            motionDetector.armed = true
            if (cfg.soundEnabled) {
                soundCues.play(Cue.RED_START)
                voice.speakPhase(isGreen = false)
            }
            val freezeTotal = cfg.redFreezeSec
            var freezeLeft = freezeTotal
            while (!finishRequested && freezeLeft > 0 && elapsedSec < totalGameSec) {
                _phase.value = GamePhase.Red(currentRound, freezeLeft, freezeTotal, elapsedSec, totalGameSec)
                delay(1000)
                freezeLeft--
                elapsedSec++
            }
            motionDetector.armed = false
        }

        motionDetector.armed = false
        if (cfg.soundEnabled) voice.speakFinish()
        _phase.value = GamePhase.Result(currentRound, sessionViolationCount)
    }

    private fun randomGreenDuration(cfg: GameSettings): Int {
        val min = cfg.greenMinSec.coerceAtLeast(1)
        val max = cfg.greenMaxSec.coerceAtLeast(min)
        return Random.nextInt(min, max + 1)
    }

    private fun onMotionTriggers(triggers: List<SectorTrigger>, image: ImageProxy) {
        val phaseNow = _phase.value
        if (phaseNow !is GamePhase.Red || processingViolation) {
            image.close()
            return
        }
        processingViolation = true
        viewModelScope.launch(Dispatchers.Default) {
            violationLock.withLock {
                try {
                    val bitmap = ImageUtils.imageProxyToBitmap(image)
                    val top = triggers.maxByOrNull { it.changedRatio } ?: return@withLock
                    val labelText = describeSector(top)
                    val marked = ImageUtils.markViolation(bitmap, top.boxFraction, labelText)

                    val saved = repository.saveViolation(
                        bitmap = marked,
                        round = currentRound,
                        lane = top.label.globalLane,
                        sideLane = top.label.sideLane,
                        side = top.label.side,
                        motionScore = top.changedRatio
                    )
                    sessionViolationCount++

                    val cfg = settings.value
                    if (cfg.soundEnabled) {
                        soundCues.play(Cue.VIOLATION)
                        voice.speakViolation(top.label)
                    }

                    _lastViolation.value = ViolationUiEvent(top.label, marked)
                    delay(OVERLAY_DURATION_MS)
                    if (_lastViolation.value?.label == top.label) {
                        _lastViolation.value = null
                    }
                } finally {
                    image.close()
                    processingViolation = false
                }
            }
        }
    }

    private fun describeSector(trigger: SectorTrigger): String = when (trigger.label.side) {
        ViolationSide.CENTER -> "По центру"
        ViolationSide.LEFT -> "Слева ${trigger.label.sideLane}"
        ViolationSide.RIGHT -> "Справа ${trigger.label.sideLane}"
    }

    override fun onCleared() {
        super.onCleared()
        voice.shutdown()
        soundCues.release()
    }

    companion object {
        private const val OVERLAY_DURATION_MS = 2500L
    }
}

class GameViewModelFactory(private val app: ZamriApp) : ViewModelProvider.Factory {
    @Suppress("UNCHECKED_CAST")
    override fun <T : ViewModel> create(modelClass: Class<T>): T {
        require(modelClass.isAssignableFrom(GameViewModel::class.java))
        return GameViewModel(app, app.repository, app.settingsStore) as T
    }
}
