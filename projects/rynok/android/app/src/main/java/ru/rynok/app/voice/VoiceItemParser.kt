package ru.rynok.app.voice

data class ParsedItem(val name: String, val quantity: String, val plannedPrice: Double?)

/**
 * Грубый разбор произнесённой фразы вроде «молоко два литра» или
 * «яблоки пять кг по восемьдесят рублей» на название/количество/цену.
 * Это эвристика, а не полноценный NLU — пользователь всегда может
 * поправить результат вручную перед отправкой списка.
 */
object VoiceItemParser {

    private val numberWords = mapOf(
        "один" to "1", "одна" to "1", "два" to "2", "две" to "2", "три" to "3",
        "четыре" to "4", "пять" to "5", "шесть" to "6", "семь" to "7",
        "восемь" to "8", "девять" to "9", "десять" to "10",
    )

    private val unitWords = listOf(
        "кг", "килограмм", "килограмма", "килограммов", "г", "грамм", "граммов",
        "л", "литр", "литра", "литров", "шт", "штук", "штуки", "штука",
        "пачка", "пачек", "пачки", "батон", "батона", "батонов", "десяток", "десятка",
    )

    private val priceRegex = Regex("""(?:по|за)\s+(\d+(?:[.,]\d+)?)\s*(?:рубл\w*|р\.?)""")
    private val quantityRegex = Regex("""(\d+(?:[.,]\d+)?)\s*(${unitWords.joinToString("|")})?""")

    fun parse(rawText: String): ParsedItem {
        var text = normalizeNumberWords(rawText.trim().lowercase())

        var price: Double? = null
        priceRegex.find(text)?.let { match ->
            price = match.groupValues[1].replace(',', '.').toDoubleOrNull()
            text = text.removeRange(match.range).trim()
        }

        var quantity = ""
        quantityRegex.find(text)?.let { match ->
            quantity = match.value.trim()
            text = text.removeRange(match.range).trim()
        }

        val name = text.trim().replaceFirstChar { if (it.isLowerCase()) it.titlecase() else it.toString() }
        return ParsedItem(
            name = name.ifBlank { rawText.trim() },
            quantity = quantity.ifBlank { "1 шт" },
            plannedPrice = price,
        )
    }

    private fun normalizeNumberWords(text: String): String {
        var result = text
        for ((word, digit) in numberWords) {
            result = result.replace(Regex("""\b$word\b"""), digit)
        }
        return result
    }
}
