package com.robutpit.screentranslator

import android.util.LruCache
import com.google.mlkit.common.model.DownloadConditions
import com.google.mlkit.nl.languageid.LanguageIdentification
import com.google.mlkit.nl.languageid.LanguageIdentificationOptions
import com.google.mlkit.nl.translate.TranslateLanguage
import com.google.mlkit.nl.translate.Translation
import com.google.mlkit.nl.translate.Translator
import com.google.mlkit.nl.translate.TranslatorOptions
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.Deferred
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.tasks.await

/**
 * Определение языка + перевод на устройстве (Google ML Kit).
 * Модель каждого языка (~30 МБ) скачивается один раз, дальше всё работает без интернета.
 */
class TranslationEngine {

    private val langId = LanguageIdentification.getClient(
        LanguageIdentificationOptions.Builder().setConfidenceThreshold(0.45f).build()
    )
    private val translators = HashMap<String, Translator>()
    private val ready = HashMap<String, Deferred<Boolean>>()
    private val lock = Mutex()

    private val translationCache = LruCache<String, String>(3000)
    private val langCache = LruCache<String, String>(3000)

    /** Код языка ML Kit или [UNKNOWN]. */
    suspend fun detect(text: String): String {
        langCache.get(text)?.let { return it }
        val tag = try { langId.identifyLanguage(text).await() } catch (e: Exception) { "und" }
        val code = if (tag == "und") UNKNOWN else TranslateLanguage.fromLanguageTag(tag) ?: UNKNOWN
        langCache.put(text, code)
        return code
    }

    /** Перевод или null, если модель недоступна (например, нет интернета для первой загрузки). */
    suspend fun translate(text: String, source: String, target: String): String? {
        if (source == target) return text
        val key = "$source|$target|$text"
        translationCache.get(key)?.let { return it }
        val translator = translator(source, target) ?: return null
        return try {
            translator.translate(text).await().also { translationCache.put(key, it) }
        } catch (e: Exception) {
            null
        }
    }

    /** Заранее скачать модель пары языков. */
    suspend fun prepare(source: String, target: String): Boolean =
        source == target || translator(source, target) != null

    @OptIn(kotlinx.coroutines.ExperimentalCoroutinesApi::class)
    private suspend fun translator(source: String, target: String): Translator? {
        val key = "$source|$target"
        val deferred = lock.withLock {
            ready[key]?.takeUnless { it.isCompleted && !it.getCompleted() } ?: run {
                val t = translators.getOrPut(key) {
                    Translation.getClient(
                        TranslatorOptions.Builder().setSourceLanguage(source).setTargetLanguage(target).build()
                    )
                }
                val d = CompletableDeferred<Boolean>()
                t.downloadModelIfNeeded(DownloadConditions.Builder().build())
                    .addOnSuccessListener { d.complete(true) }
                    .addOnFailureListener { d.complete(false) }
                ready[key] = d
                d
            }
        }
        return if (deferred.await()) translators[key] else null
    }

    /**
     * Переводит набор фраз с экрана. Язык каждой фразы определяется отдельно; для коротких
     * подписей («OK», «Settings»), где язык не ясен, берётся самый частый язык на экране.
     * Фразы, уже написанные на целевом языке, пропускаются (в результате их нет).
     */
    suspend fun translateAll(texts: List<String>, target: String, fallback: String): Map<String, String> =
        coroutineScope {
            val unique = texts.distinct()
            val langs = unique.map { async { it to detect(it) } }.awaitAll().toMap()
            val dominant = langs.values.filter { it != UNKNOWN }
                .groupingBy { it }.eachCount().maxByOrNull { it.value }?.key
            val guess = dominant ?: fallback
            unique.map { text ->
                async {
                    var src = langs[text] ?: UNKNOWN
                    if (src == UNKNOWN) {
                        if (looksLikeScriptOf(text, target)) return@async null
                        src = guess
                    }
                    if (src == target) return@async null
                    val tr = translate(text, src, target) ?: return@async null
                    if (tr.equals(text, ignoreCase = true)) null else text to tr
                }
            }.awaitAll().filterNotNull().toMap()
        }

    fun close() {
        langId.close()
        translators.values.forEach { it.close() }
    }

    /** Быстрая проверка: текст без определённого языка, но написан кириллицей при переводе на русский и т. п. */
    private fun looksLikeScriptOf(text: String, target: String): Boolean {
        val letters = text.filter { it.isLetter() }
        if (letters.isEmpty()) return true
        val cyr = letters.count { Character.UnicodeBlock.of(it) == Character.UnicodeBlock.CYRILLIC }
        val cyrillicTargets = setOf("ru", "uk", "be", "bg", "mk")
        return if (target in cyrillicTargets) cyr * 2 > letters.length else false
    }

    companion object {
        const val UNKNOWN = "und"
    }
}
