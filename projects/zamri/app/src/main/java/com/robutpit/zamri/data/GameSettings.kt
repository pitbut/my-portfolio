package com.robutpit.zamri.data

/**
 * All tunable knobs exposed on the Settings screen.
 *
 * @param roundDurationSec total game length; the phase loop runs until this
 *   elapses or the player taps "Finish".
 * @param greenMinSec / greenMaxSec random range the "green light" phase is
 *   drawn from on every cycle, so players can't predict the switch.
 * @param redFreezeSec how long the motion detector stays armed after the
 *   doll turns around, before the next green phase can start.
 * @param sectorCount how many vertical lanes the camera frame is split
 *   into for motion analysis.
 * @param soundEnabled toggles both the TTS callouts and the start/stop cues.
 * @param volumePercent 0..100, applied to STREAM_MUSIC.
 * @param sensitivityPercent 0..100; higher means smaller motions trigger a
 *   violation (lower binarization threshold / changed-pixel ratio).
 */
data class GameSettings(
    val roundDurationSec: Int = 120,
    val greenMinSec: Int = 3,
    val greenMaxSec: Int = 8,
    val redFreezeSec: Int = 4,
    val sectorCount: Int = 5,
    val soundEnabled: Boolean = true,
    val volumePercent: Int = 80,
    val sensitivityPercent: Int = 50
) {
    companion object {
        const val MIN_SECTORS = 3
        const val MAX_SECTORS = 9
    }
}
