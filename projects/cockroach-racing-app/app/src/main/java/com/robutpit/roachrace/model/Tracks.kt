package com.robutpit.roachrace.model

data class Obstacle(val pos: Float, val slow: Float)

data class Track(
    val id: String,
    val displayName: String,
    val description: String,
    val distance: Float,
    val friction: Float,
    val obstacles: List<Obstacle>,
    val tags: List<String>,
    /** Background tint so each track is visually unmistakable on the race
     * screen, not just numerically different. */
    val themeColor: Long,
    val emoji: String,
)

val TRACKS = listOf(
    Track(
        id = "table",
        displayName = "Стол переговоров",
        description = "Нейтральная трасса, чуть скользкая от полироли",
        distance = 1000f,
        friction = 1.00f,
        obstacles = emptyList(),
        tags = listOf("Баланс"),
        themeColor = 0xFF20241C,
        emoji = "🗂️",
    ),
    Track(
        id = "kitchen",
        displayName = "Кухня",
        description = "Крошки и пятна кофе — сложнее держать курс",
        distance = 1000f,
        friction = 1.35f,
        obstacles = listOf(Obstacle(0.5f, 0.35f)),
        tags = listOf("Стрессоустойчивость", "Контроль"),
        themeColor = 0xFF2A2013,
        emoji = "☕",
    ),
    Track(
        id = "corridor",
        displayName = "Коридор с преградами",
        description = "Степлер, скрепки и чашка на пути",
        distance = 1050f,
        friction = 1.05f,
        obstacles = listOf(Obstacle(0.22f, 0.5f), Obstacle(0.5f, 0.5f), Obstacle(0.78f, 0.5f)),
        tags = listOf("Скорость", "Манёвр"),
        themeColor = 0xFF1C2430,
        emoji = "📎",
    ),
    Track(
        id = "gym",
        displayName = "Переговорка (марафон)",
        description = "Длинная дистанция — экзамен на выносливость",
        distance = 1700f,
        friction = 1.00f,
        obstacles = listOf(Obstacle(0.6f, 0.3f)),
        tags = listOf("Выносливость"),
        themeColor = 0xFF241C2A,
        emoji = "🏃",
    ),
)

fun trackById(id: String): Track = TRACKS.firstOrNull { it.id == id } ?: TRACKS[0]
