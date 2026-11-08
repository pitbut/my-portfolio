package com.robutpit.screentranslator

import android.accessibilityservice.AccessibilityService
import android.content.Intent
import android.content.SharedPreferences
import android.graphics.PixelFormat
import android.graphics.Rect
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.view.Gravity
import android.view.WindowManager
import android.view.accessibility.AccessibilityEvent
import android.widget.Toast
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

/**
 * Главная служба. Следит за изменениями на экране, собирает текст, переводит и рисует перевод
 * поверх. Окна-оверлеи типа TYPE_ACCESSIBILITY_OVERLAY не требуют разрешения «поверх других
 * приложений» и не перехватывают касания — приложение под ними работает как обычно.
 */
class TranslatorService : AccessibilityService(), SharedPreferences.OnSharedPreferenceChangeListener {

    private lateinit var prefs: Prefs
    private lateinit var wm: WindowManager
    private lateinit var overlay: OverlayView
    private lateinit var bubble: BubbleController
    private val engine = TranslationEngine()
    private val ocr = OcrScanner()
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main)
    private val handler = Handler(Looper.getMainLooper())

    /** Пользователь нажал «оригинал»: перевод спрятан до следующего нажатия. */
    private var showingOriginal = false
    /** На экране результат OCR — не перезаписываем его, пока экран не прокрутят/сменят. */
    private var ocrLock = false
    private var generation = 0
    private var lastSignature = 0
    private var lastAutoOcr = 0L
    private var foregroundPkg: String? = null

    private val scanRunnable = Runnable { scan() }

    override fun onServiceConnected() {
        super.onServiceConnected()
        instance = this
        prefs = Prefs(this)
        wm = getSystemService(WINDOW_SERVICE) as WindowManager
        overlay = OverlayView(this).apply {
            dark = prefs.darkStyle
            textScale = prefs.textScale
        }
        val lp = WindowManager.LayoutParams(
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
                WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE or
                WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN or
                WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS,
            PixelFormat.TRANSLUCENT
        ).apply {
            gravity = Gravity.TOP or Gravity.START
            if (Build.VERSION.SDK_INT >= 28) {
                layoutInDisplayCutoutMode = WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_SHORT_EDGES
            }
        }
        wm.addView(overlay, lp)

        bubble = BubbleController(this, wm, prefs, bubbleListener)
        if (prefs.showBubble) bubble.show()
        updateBubbleState()
        prefs.sp.registerOnSharedPreferenceChangeListener(this)
        schedule(300)
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent) {
        val pkg = event.packageName?.toString()
        if (pkg == packageName) return
        if (!prefs.enabled || showingOriginal) return
        when (event.eventType) {
            AccessibilityEvent.TYPE_VIEW_SCROLLED,
            AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED -> {
                // Экран сдвинулся — старые плашки стоят не на своих местах, убираем сразу.
                ocrLock = false
                overlay.clear()
                lastSignature = 0
                schedule(450)
            }
            else -> if (!ocrLock) schedule(350)
        }
    }

    private fun schedule(delayMs: Long) {
        handler.removeCallbacks(scanRunnable)
        handler.postDelayed(scanRunnable, delayMs)
    }

    private fun screenRect(): Rect {
        val dm = resources.displayMetrics
        return if (Build.VERSION.SDK_INT >= 30) Rect(wm.currentWindowMetrics.bounds)
        else {
            val m = android.util.DisplayMetrics()
            @Suppress("DEPRECATION") wm.defaultDisplay.getRealMetrics(m)
            Rect(0, 0, maxOf(m.widthPixels, dm.widthPixels), maxOf(m.heightPixels, dm.heightPixels))
        }
    }

    private fun scan() {
        if (!prefs.enabled || showingOriginal || ocrLock) return
        val snap = ScreenTextCollector.collect(this, screenRect())
        if (snap.packageName == packageName) {
            // На экране наши же настройки — переводить нечего.
            overlay.clear(); lastSignature = 0
            return
        }
        foregroundPkg = snap.packageName ?: foregroundPkg
        if (snap.packageName != null && snap.packageName in prefs.excluded) {
            overlay.clear(); lastSignature = 0
            return
        }
        if (snap.items.isEmpty()) {
            overlay.clear(); lastSignature = 0
            val now = System.currentTimeMillis()
            if (prefs.autoOcr && Build.VERSION.SDK_INT >= 30 && now - lastAutoOcr > 2500) {
                lastAutoOcr = now
                runOcr(manual = false)
            }
            return
        }
        val signature = snap.items.hashCode() * 31 + prefs.target.hashCode()
        if (signature == lastSignature && overlay.isShowing) return
        lastSignature = signature
        render(snap.items)
    }

    private fun render(items: List<TextItem>) {
        val gen = ++generation
        val target = prefs.target
        val fallback = prefs.fallbackSource
        scope.launch {
            val map = engine.translateAll(items.map { it.text }, target, fallback)
            if (gen != generation || showingOriginal) return@launch
            overlay.show(items.mapNotNull { item -> map[item.text]?.let { item.bounds to it } })
        }
    }

    private fun runOcr(manual: Boolean) {
        if (Build.VERSION.SDK_INT < 30) {
            if (manual) toast("Распознавание с экрана доступно с Android 11")
            return
        }
        val gen = ++generation
        scope.launch {
            bubble.setState(BubbleController.State.BUSY)
            overlay.clear()
            bubble.setInvisible(true)
            delay(120) // дать системе перерисовать экран без наших окон
            val result = ocr.scan(this@TranslatorService, prefs.ocrScript)
            bubble.setInvisible(false)
            updateBubbleState()
            if (gen != generation) return@launch
            when (result) {
                is OcrScanner.Result.Ok -> {
                    if (result.items.isEmpty()) {
                        if (manual) toast("Текст на экране не найден")
                        return@launch
                    }
                    ocrLock = manual
                    showingOriginal = false
                    updateBubbleState()
                    val map = engine.translateAll(result.items.map { it.text }, prefs.target, prefs.fallbackSource)
                    if (gen != generation) return@launch
                    overlay.show(result.items.mapNotNull { i -> map[i.text]?.let { i.bounds to it } })
                    if (manual && map.isEmpty()) toast("Текст уже на нужном языке или модель ещё загружается")
                }
                OcrScanner.Result.Secure -> if (manual) toast(
                    "Это окно запрещает снимки экрана. Обычный перевод текста здесь продолжает работать."
                )
                OcrScanner.Result.TooFrequent -> if (manual) toast("Слишком часто, попробуйте через секунду")
                else -> if (manual) toast("Не удалось сделать снимок экрана")
            }
        }
    }

    private fun toggleOriginal() {
        showingOriginal = !showingOriginal
        generation++
        if (showingOriginal) {
            overlay.clear()
        } else {
            ocrLock = false
            lastSignature = 0
            schedule(50)
        }
        updateBubbleState()
    }

    private fun updateBubbleState() {
        bubble.setState(
            when {
                !prefs.enabled -> BubbleController.State.PAUSED
                showingOriginal -> BubbleController.State.ORIGINAL
                else -> BubbleController.State.TRANSLATED
            }
        )
    }

    private val bubbleListener = object : BubbleController.Listener {
        override fun onBubbleTap() {
            if (!prefs.enabled) {
                prefs.enabled = true
                toast("Перевод включён")
                return
            }
            toggleOriginal()
        }

        override fun menuItems(): List<Pair<String, () -> Unit>> {
            val pkg = foregroundPkg
            val list = ArrayList<Pair<String, () -> Unit>>()
            if (prefs.enabled) {
                list += (if (showingOriginal) "🔤  Показать перевод" else "👁  Показать оригинал") to { toggleOriginal() }
                list += "📷  Перевести с картинки (OCR)" to { runOcr(manual = true) }
                list += "⏸  Пауза" to { prefs.enabled = false }
            } else {
                list += "▶  Включить перевод" to { prefs.enabled = true }
            }
            if (pkg != null) {
                val label = appLabel(pkg)
                list += if (pkg in prefs.excluded) "✅  Переводить в «$label»" to { prefs.toggleExcluded(pkg) }
                else "🚫  Не переводить в «$label»" to { prefs.toggleExcluded(pkg) }
            }
            list += "⚙  Настройки" to {
                startActivity(Intent(this@TranslatorService, MainActivity::class.java)
                    .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
            }
            list += "✖  Скрыть кнопку" to {
                prefs.showBubble = false
                toast("Кнопку можно вернуть в настройках приложения")
            }
            return list
        }
    }

    private fun appLabel(pkg: String): String = try {
        packageManager.getApplicationLabel(packageManager.getApplicationInfo(pkg, 0)).toString()
    } catch (_: Exception) {
        pkg
    }

    override fun onSharedPreferenceChanged(sp: SharedPreferences?, key: String?) {
        when (key) {
            Prefs.K_ENABLED -> {
                if (!prefs.enabled) { generation++; overlay.clear() } else { showingOriginal = false; schedule(50) }
                updateBubbleState()
            }
            Prefs.K_BUBBLE -> if (prefs.showBubble) { bubble.show(); updateBubbleState() } else bubble.hide()
            Prefs.K_DARK, Prefs.K_SCALE, Prefs.K_TARGET, Prefs.K_FALLBACK, Prefs.K_EXCLUDED -> {
                overlay.dark = prefs.darkStyle
                overlay.textScale = prefs.textScale
                lastSignature = 0
                ocrLock = false
                overlay.clear()
                updateBubbleState()
                schedule(50)
            }
        }
    }

    private fun toast(msg: String) = Toast.makeText(this, msg, Toast.LENGTH_LONG).show()

    override fun onInterrupt() {}

    override fun onDestroy() {
        instance = null
        handler.removeCallbacksAndMessages(null)
        if (::prefs.isInitialized) prefs.sp.unregisterOnSharedPreferenceChangeListener(this)
        if (::bubble.isInitialized) bubble.hide()
        if (::overlay.isInitialized) runCatching { wm.removeView(overlay) }
        scope.cancel()
        engine.close()
        ocr.close()
        super.onDestroy()
    }

    companion object {
        @Volatile
        var instance: TranslatorService? = null
            private set
    }
}
