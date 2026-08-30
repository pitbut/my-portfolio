package com.robutpit.roachrace.bluetooth

import com.robutpit.roachrace.engine.RaceEngine
import com.robutpit.roachrace.model.Breed
import com.robutpit.roachrace.model.Levels

/** Tiny line-based text protocol for the 2-phone Bluetooth link. Nothing
 * fancy — one message per line, fields pipe-separated — kept hand-rolled
 * instead of pulling in a serialization library for a handful of fields. */
object RaceProtocol {

    fun hello(name: String, breed: Breed, colorLong: Long, levels: Levels): String =
        "HELLO|$name|${breed.name}|$colorLong|${levels.speed}|${levels.stamina}|${levels.stress}"

    data class Hello(val name: String, val breed: Breed, val colorLong: Long, val levels: Levels)

    fun parseHello(line: String): Hello? {
        val p = line.split("|")
        if (p.size != 7 || p[0] != "HELLO") return null
        val breed = Breed.entries.firstOrNull { it.name == p[2] } ?: return null
        return Hello(
            name = p[1],
            breed = breed,
            colorLong = p[3].toLongOrNull() ?: 0xFFB5541EL,
            levels = Levels(
                speed = p[4].toIntOrNull() ?: 0,
                stamina = p[5].toIntOrNull() ?: 0,
                stress = p[6].toIntOrNull() ?: 0,
            ),
        )
    }

    fun track(trackId: String) = "TRACK|$trackId"
    fun parseTrack(line: String): String? {
        val p = line.split("|")
        return if (p.size == 2 && p[0] == "TRACK") p[1] else null
    }

    fun start() = "START"

    fun spook(label: String) = "SPOOK|$label"
    fun parseSpook(line: String): String? {
        val p = line.split("|")
        return if (p.size == 2 && p[0] == "SPOOK") p[1] else null
    }

    fun state(engine: RaceEngine): String {
        val body = engine.racers.mapIndexed { i, r ->
            "$i:${r.progress.floatValue}:${r.wobbleCur.value}:${r.spookTimer.value}:${if (r.finished.value) 1 else 0}"
        }.joinToString(";")
        return "STATE|${engine.elapsed}|$body"
    }

    /** index -> (progress, wobble, spook, finished) */
    fun parseState(line: String): List<StateEntry>? {
        val p = line.split("|")
        if (p.size != 3 || p[0] != "STATE") return null
        return p[2].split(";").filter { it.isNotBlank() }.mapNotNull { chunk ->
            val f = chunk.split(":")
            if (f.size != 5) return@mapNotNull null
            StateEntry(
                index = f[0].toIntOrNull() ?: return@mapNotNull null,
                progress = f[1].toFloatOrNull() ?: 0f,
                wobble = f[2].toFloatOrNull() ?: 0f,
                spook = f[3].toFloatOrNull() ?: 0f,
                finished = f[4] == "1",
            )
        }
    }

    data class StateEntry(val index: Int, val progress: Float, val wobble: Float, val spook: Float, val finished: Boolean)
}
