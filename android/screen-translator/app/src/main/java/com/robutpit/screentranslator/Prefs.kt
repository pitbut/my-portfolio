package com.robutpit.screentranslator

import android.content.Context
import android.content.SharedPreferences
import com.google.mlkit.nl.translate.TranslateLanguage
import java.util.Locale

/** Все настройки приложения в одном месте. Служба слушает изменения и применяет их сразу. */
class Prefs(context: Context) {
    val sp: SharedPreferences = context.getSharedPreferences("settings", Context.MODE_PRIVATE)

    /** Переводить автоматически (false = пауза). */
    var enabled: Boolean
        get() = sp.getBoolean(K_ENABLED, true)
        set(v) = sp.edit().putBoolean(K_ENABLED, v).apply()

    /** Язык, на который переводим. */
    var target: String
        get() = sp.getString(K_TARGET, null) ?: defaultTarget()
        set(v) = sp.edit().putString(K_TARGET, v).apply()

    /** Язык, который считаем исходным, если определить язык короткой фразы не удалось. */
    var fallbackSource: String
        get() = sp.getString(K_FALLBACK, TranslateLanguage.ENGLISH)!!
        set(v) = sp.edit().putString(K_FALLBACK, v).apply()

    /** Если обычным способом текст не найден (игры, картинки) — распознавать его с экрана. */
    var autoOcr: Boolean
        get() = sp.getBoolean(K_AUTO_OCR, false)
        set(v) = sp.edit().putBoolean(K_AUTO_OCR, v).apply()

    /** Письменность для OCR: latin / chinese / japanese / korean. */
    var ocrScript: String
        get() = sp.getString(K_OCR_SCRIPT, "latin")!!
        set(v) = sp.edit().putString(K_OCR_SCRIPT, v).apply()

    /** Тёмные или светлые плашки перевода. */
    var darkStyle: Boolean
        get() = sp.getBoolean(K_DARK, true)
        set(v) = sp.edit().putBoolean(K_DARK, v).apply()

    /** Масштаб текста перевода, 0.7..1.5. */
    var textScale: Float
        get() = sp.getFloat(K_SCALE, 1f)
        set(v) = sp.edit().putFloat(K_SCALE, v).apply()

    var showBubble: Boolean
        get() = sp.getBoolean(K_BUBBLE, true)
        set(v) = sp.edit().putBoolean(K_BUBBLE, v).apply()

    var bubbleX: Int
        get() = sp.getInt(K_BX, -1)
        set(v) = sp.edit().putInt(K_BX, v).apply()

    var bubbleY: Int
        get() = sp.getInt(K_BY, -1)
        set(v) = sp.edit().putInt(K_BY, v).apply()

    /** Приложения, в которых не переводим. */
    var excluded: Set<String>
        get() = sp.getStringSet(K_EXCLUDED, emptySet())!!.toSet()
        set(v) = sp.edit().putStringSet(K_EXCLUDED, v).apply()

    fun toggleExcluded(pkg: String) {
        excluded = if (pkg in excluded) excluded - pkg else excluded + pkg
    }

    companion object {
        const val K_ENABLED = "enabled"
        const val K_TARGET = "target"
        const val K_FALLBACK = "fallback_source"
        const val K_AUTO_OCR = "auto_ocr"
        const val K_OCR_SCRIPT = "ocr_script"
        const val K_DARK = "dark_style"
        const val K_SCALE = "text_scale"
        const val K_BUBBLE = "show_bubble"
        const val K_BX = "bubble_x"
        const val K_BY = "bubble_y"
        const val K_EXCLUDED = "excluded"

        private fun defaultTarget(): String {
            val sys = Locale.getDefault().language
            return TranslateLanguage.fromLanguageTag(sys)?.takeIf { it != TranslateLanguage.ENGLISH }
                ?: TranslateLanguage.RUSSIAN
        }
    }
}

object Languages {
    private val ru = Locale("ru")

    /** Все языки ML Kit с названиями по-русски, отсортированные по алфавиту. */
    val all: List<Pair<String, String>> by lazy {
        TranslateLanguage.getAllLanguages()
            .map { it to name(it) }
            .sortedBy { it.second }
    }

    fun name(code: String): String =
        Locale(code).getDisplayLanguage(ru).replaceFirstChar { it.titlecase(ru) }
}
