package ru.rynok.app.domain

import ru.rynok.app.data.repository.BudgetSnapshot
import java.util.Locale
import kotlin.math.abs
import kotlin.math.roundToInt

fun formatMoney(amount: Double): String {
    val rounded = amount.roundToInt()
    val formatted = String.format(Locale("ru"), "%,d", rounded).replace(',', ' ')
    return "$formatted ₽"
}

/** Текст для озвучивания кнопкой "Итоговый бюджет". */
fun budgetAnnouncement(snapshot: BudgetSnapshot): String {
    val diff = snapshot.difference
    return when {
        abs(diff) < 1.0 -> "Уложились точно в бюджет, потрачено ${formatMoney(snapshot.actual)}"
        diff > 0 -> "Перерасход на ${formatMoney(diff)}. Потрачено ${formatMoney(snapshot.actual)} из ${formatMoney(snapshot.planned)}"
        else -> "Экономия ${formatMoney(-diff)}. Потрачено ${formatMoney(snapshot.actual)} из ${formatMoney(snapshot.planned)}"
    }
}
