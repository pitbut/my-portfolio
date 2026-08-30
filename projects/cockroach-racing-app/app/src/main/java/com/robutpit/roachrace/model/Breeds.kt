package com.robutpit.roachrace.model

enum class Breed(
    val displayName: String,
    val description: String,
    val sizeDp: Float,
    val baseSpeed: Float,
    val baseStamina: Float,
    val baseStress: Float,
) {
    PRUSAK("Прусак", "Мелкий и шустрый, но нервный", 15f, 1.18f, 0.78f, 0.72f),
    BLACK("Чёрный таракан", "Универсал, хорошо обучается", 19f, 1.00f, 1.00f, 1.00f),
    MADAGASCAR("Мадагаскарский шипящий", "Крупный танк, почти не устаёт", 26f, 0.84f, 1.35f, 1.32f),
    ALBINO("Альбинос", "Редкий, сбалансированный", 18f, 1.06f, 0.95f, 1.08f);

    companion object {
        fun random() = entries.random()
    }
}

data class RoachColor(val id: String, val displayName: String, val colorLong: Long)

val ROACH_COLORS = listOf(
    RoachColor("rust", "Ржавый", 0xFFB5541E),
    RoachColor("dark", "Тёмный шоколад", 0xFF3B2A20),
    RoachColor("sand", "Песочный", 0xFFC9A869),
    RoachColor("pale", "Бледный альбинос", 0xFFE8DCC8),
    RoachColor("crimson", "Багровый", 0xFF8C2F2F),
    RoachColor("olive", "Оливковый", 0xFF5C6B3A),
)

fun colorById(id: String): RoachColor = ROACH_COLORS.firstOrNull { it.id == id } ?: ROACH_COLORS[0]
