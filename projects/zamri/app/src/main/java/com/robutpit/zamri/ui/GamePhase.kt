package com.robutpit.zamri.ui

/** The game's top-level state machine: Idle -> Countdown -> (Green <-> Red)* -> Result. */
sealed interface GamePhase {
    data object Idle : GamePhase

    data class Countdown(val secondsLeft: Int) : GamePhase

    data class Green(
        val round: Int,
        val gameElapsedSec: Int,
        val totalGameSec: Int
    ) : GamePhase

    data class Red(
        val round: Int,
        val freezeSecondsLeft: Int,
        val freezeTotalSec: Int,
        val gameElapsedSec: Int,
        val totalGameSec: Int
    ) : GamePhase

    data class Result(
        val roundsPlayed: Int,
        val violationsCount: Int
    ) : GamePhase
}
