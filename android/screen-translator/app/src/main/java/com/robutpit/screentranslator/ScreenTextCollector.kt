package com.robutpit.screentranslator

import android.accessibilityservice.AccessibilityService
import android.graphics.Rect
import android.os.Build
import android.view.accessibility.AccessibilityNodeInfo
import android.view.accessibility.AccessibilityWindowInfo

data class TextItem(val text: String, val bounds: Rect)

data class ScreenSnapshot(val packageName: String?, val items: List<TextItem>)

/**
 * Собирает текст с экрана через API специальных возможностей.
 *
 * Важно для Telegram: в чатах с «запретом копирования» Telegram блокирует выделение, пересылку,
 * встроенный перевод и скриншоты (FLAG_SECURE), но текст сообщений он всё равно отдаёт
 * службам спец. возможностей (иначе TalkBack не смог бы читать их незрячим). Поэтому мы
 * берём текст отсюда, а не со скриншота, — и ограничение на перевод не влияет.
 */
object ScreenTextCollector {

    private const val MAX_ITEMS = 150
    private const val MAX_DEPTH = 70

    fun collect(service: AccessibilityService, screen: Rect): ScreenSnapshot {
        val own = service.packageName
        val items = ArrayList<TextItem>()
        var pkg: String? = null
        // Окна, лежащие поверх текущего: клавиатура, панели системы, всплывающие окна.
        // Текст под ними не виден человеку, и плашки туда ставить нельзя.
        val covers = ArrayList<Rect>()

        val windows = try { service.windows } catch (_: Exception) { emptyList() }
        // getWindows() отдаёт окна сверху вниз по слоям.
        for (w in windows) {
            if (w.type == AccessibilityWindowInfo.TYPE_ACCESSIBILITY_OVERLAY) continue
            val wb = Rect().also { w.getBoundsInScreen(it) }
            if (w.type == AccessibilityWindowInfo.TYPE_APPLICATION) {
                val root = w.root
                val p = root?.packageName?.toString()
                if (pkg == null && p != null) pkg = p
                if (root != null && p != own && items.size < MAX_ITEMS) {
                    walk(root, 0, screen, covers, items)
                }
            }
            // Почти полноэкранное системное окно считаем перекрытием, только если оно активно
            // (открытая шторка уведомлений), иначе прозрачные служебные окна прошивок блокировали бы всё.
            val huge = wb.width() * wb.height() > screen.width() * screen.height() * 0.85f
            if (w.type == AccessibilityWindowInfo.TYPE_APPLICATION || w.type == AccessibilityWindowInfo.TYPE_INPUT_METHOD ||
                !huge || w.isActive || w.isFocused
            ) covers += wb
        }
        if (windows.isEmpty()) {
            service.rootInActiveWindow?.let { root ->
                pkg = root.packageName?.toString()
                if (pkg != own) walk(root, 0, screen, covers, items)
            }
        }
        return ScreenSnapshot(pkg, items.take(MAX_ITEMS))
    }

    /** Возвращает true, если в поддереве нашёлся текст. */
    private fun walk(
        node: AccessibilityNodeInfo, depth: Int, screen: Rect, covers: List<Rect>, out: MutableList<TextItem>
    ): Boolean {
        if (depth > MAX_DEPTH || out.size >= MAX_ITEMS) return false
        if (!node.isVisibleToUser) return false
        // Поля ввода не трогаем, чтобы не закрывать то, что человек печатает.
        if (node.isEditable || node.isPassword) return false

        var childHasText = false
        for (i in 0 until node.childCount) {
            val child = node.getChild(i) ?: continue
            if (walk(child, depth + 1, screen, covers, out)) childHasText = true
            recycle(child)
        }
        if (childHasText) return true

        val raw = node.text?.toString()?.takeIf { it.isNotBlank() }
            ?: node.contentDescription?.toString()?.takeIf { it.isNotBlank() && it.length >= 2 }
            ?: return false
        val text = clean(raw) ?: return false

        val r = Rect()
        node.getBoundsInScreen(r)
        if (r.width() < 8 || r.height() < 8) return false
        if (!r.intersect(screen)) return false
        if (covers.any { it.contains(r.centerX(), r.centerY()) }) return false
        out += TextItem(text, r)
        return true
    }

    private fun clean(s: String): String? {
        val t = s.trim().replace(Regex("[ \\t]+"), " ")
        if (t.length < 2) return null
        // Нужна хотя бы пара букв: время, числа, смайлы переводить не нужно.
        if (t.count { it.isLetter() } < 2) return null
        if (t.startsWith("http://") || t.startsWith("https://")) return null
        return t.take(2000)
    }

    @Suppress("DEPRECATION")
    private fun recycle(n: AccessibilityNodeInfo) {
        if (Build.VERSION.SDK_INT < 33) try { n.recycle() } catch (_: Exception) {}
    }
}
