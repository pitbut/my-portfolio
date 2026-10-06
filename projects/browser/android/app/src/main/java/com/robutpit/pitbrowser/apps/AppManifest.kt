package com.robutpit.pitbrowser.apps

import org.json.JSONObject

/**
 * manifest.json внутри пакета .pitapp. Формат описан в projects/browser/sdk/README.md.
 */
data class AppManifest(
    val id: String,
    val name: String,
    val version: String,
    val entry: String,
    val icon: String?,
    val description: String,
    val orientation: String,
    val permissions: Set<String>,
    /** "desc" — больше очков лучше, "asc" — меньше лучше (например, время прохождения). */
    val scoreOrder: String,
    val scoreUnit: String,
) {
    /** Адрес приложения: у каждого своё происхождение (origin) — свои localStorage, cookie и рекорды. */
    val origin: String get() = "https://$id.$APP_DOMAIN"
    val entryUrl: String get() = "$origin/$entry"

    fun has(permission: String) = permission in permissions

    companion object {
        const val APP_DOMAIN = "pitapp.robutpit.com"

        /** Разрешения, которые может запросить приложение. */
        val PERMISSIONS = linkedMapOf(
            "sensors" to "датчики движения и окружения",
            "vibrate" to "вибрация",
            "scores" to "таблица рекордов",
            "screen" to "управление экраном (не гаснуть, поворот)",
            "camera" to "камера",
            "microphone" to "микрофон",
            "geolocation" to "местоположение",
            "network" to "доступ в интернет",
        )

        /** Опасные разрешения: кроме согласия при установке, спрашиваются при первом использовании. */
        val RUNTIME = setOf("camera", "microphone", "geolocation")

        private val ID = Regex("^[a-z0-9][a-z0-9-]{1,39}$")
        private val ORIENTATIONS = setOf("any", "portrait", "landscape")

        /** @throws InvalidPackageException если манифест некорректен */
        fun parse(json: String): AppManifest {
            val o = try { JSONObject(json) } catch (e: Exception) { throw InvalidPackageException("manifest.json: неверный JSON") }
            val id = o.optString("id")
            if (!ID.matches(id)) throw InvalidPackageException("id должен состоять из a-z, 0-9 и «-» (2–40 символов): «$id»")
            val name = o.optString("name").trim()
            if (name.isEmpty() || name.length > 60) throw InvalidPackageException("name обязателен (до 60 символов)")
            val entry = o.optString("entry", "index.html").trimStart('/')
            if (!isSafePath(entry)) throw InvalidPackageException("entry: недопустимый путь «$entry»")
            val icon = o.optString("icon").trimStart('/').takeIf { it.isNotEmpty() }
            if (icon != null && !isSafePath(icon)) throw InvalidPackageException("icon: недопустимый путь «$icon»")
            val orientation = o.optString("orientation", "any")
            if (orientation !in ORIENTATIONS) throw InvalidPackageException("orientation: any, portrait или landscape")
            val perms = linkedSetOf<String>()
            o.optJSONArray("permissions")?.let { arr ->
                for (i in 0 until arr.length()) {
                    val p = arr.optString(i)
                    if (p !in PERMISSIONS) throw InvalidPackageException("неизвестное разрешение «$p»")
                    perms += p
                }
            }
            val scores = o.optJSONObject("scores")
            val order = scores?.optString("order", "desc") ?: "desc"
            if (order != "desc" && order != "asc") throw InvalidPackageException("scores.order: desc или asc")
            return AppManifest(
                id = id,
                name = name,
                version = o.optString("version", "1.0.0").take(20),
                entry = entry,
                icon = icon,
                description = o.optString("description").take(500),
                orientation = orientation,
                permissions = perms,
                scoreOrder = order,
                scoreUnit = scores?.optString("unit").orEmpty().take(20),
            )
        }

        /** Относительный путь без выхода за пределы пакета. */
        fun isSafePath(p: String): Boolean =
            p.isNotEmpty() && p.length < 300 && !p.startsWith("/") && !p.contains('\\') && !p.contains('\u0000') &&
                p.split('/').none { it == ".." || it == "." || it.isEmpty() }
    }
}

class InvalidPackageException(message: String) : Exception(message)
