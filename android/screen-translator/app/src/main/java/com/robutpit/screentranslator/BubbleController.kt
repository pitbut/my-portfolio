package com.robutpit.screentranslator

import android.annotation.SuppressLint
import android.content.Context
import android.graphics.PixelFormat
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.os.Handler
import android.os.Looper
import android.view.Gravity
import android.view.MotionEvent
import android.view.View
import android.view.ViewConfiguration
import android.view.WindowManager
import android.widget.LinearLayout
import android.widget.TextView
import kotlin.math.abs

/**
 * Плавающая кнопка поверх всех приложений.
 *  • нажатие      — показать оригинал / снова перевод;
 *  • удержание    — меню (OCR, пауза, исключить приложение, настройки);
 *  • перетаскивание — переместить кнопку.
 */
class BubbleController(
    private val context: Context,
    private val wm: WindowManager,
    private val prefs: Prefs,
    private val listener: Listener,
) {
    interface Listener {
        fun onBubbleTap()
        fun menuItems(): List<Pair<String, () -> Unit>>
    }

    enum class State { TRANSLATED, ORIGINAL, PAUSED, BUSY }

    private val density = context.resources.displayMetrics.density
    private val size = (48 * density).toInt()
    private val handler = Handler(Looper.getMainLooper())
    private var bubble: TextView? = null
    private var params: WindowManager.LayoutParams? = null
    private var menu: View? = null
    private var state = State.TRANSLATED

    val isShown get() = bubble != null

    @SuppressLint("ClickableViewAccessibility")
    fun show() {
        if (bubble != null) return
        val dm = context.resources.displayMetrics
        val p = WindowManager.LayoutParams(
            size, size,
            WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS,
            PixelFormat.TRANSLUCENT
        ).apply {
            gravity = Gravity.TOP or Gravity.START
            x = prefs.bubbleX.takeIf { it >= 0 } ?: (dm.widthPixels - size - (8 * density).toInt())
            y = prefs.bubbleY.takeIf { it >= 0 } ?: (dm.heightPixels * 0.35f).toInt()
        }
        val v = TextView(context).apply {
            gravity = Gravity.CENTER
            textSize = 13f
            typeface = Typeface.DEFAULT_BOLD
            elevation = 6 * density
            contentDescription = "Экранный переводчик"
        }
        v.setOnTouchListener(DragTouch(p, v))
        wm.addView(v, p)
        bubble = v
        params = p
        render()
    }

    fun hide() {
        dismissMenu()
        bubble?.let { runCatching { wm.removeView(it) } }
        bubble = null
    }

    fun setState(s: State) {
        state = s
        render()
    }

    private fun render() {
        val v = bubble ?: return
        val (label, color) = when (state) {
            State.TRANSLATED -> prefs.target.uppercase() to 0xFF1E6FD9.toInt()
            State.ORIGINAL -> "ОРИГ" to 0xFF5F6368.toInt()
            State.PAUSED -> "❚❚" to 0xAA5F6368.toInt()
            State.BUSY -> "…" to 0xFF1E6FD9.toInt()
        }
        v.text = label
        v.setTextColor(0xFFFFFFFF.toInt())
        v.textSize = if (label.length > 3) 11f else 14f
        v.background = GradientDrawable().apply {
            shape = GradientDrawable.OVAL
            setColor(color)
            setStroke((2 * density).toInt(), 0x66FFFFFF)
        }
        v.alpha = if (state == State.PAUSED) 0.6f else 0.92f
    }

    /** Временно спрятать кнопку (чтобы она не попала в снимок для OCR). */
    fun setInvisible(invisible: Boolean) {
        bubble?.visibility = if (invisible) View.INVISIBLE else View.VISIBLE
    }

    private inner class DragTouch(private val p: WindowManager.LayoutParams, private val v: View) :
        View.OnTouchListener {
        private val slop = ViewConfiguration.get(context).scaledTouchSlop
        private var downX = 0f
        private var downY = 0f
        private var startX = 0
        private var startY = 0
        private var dragging = false
        private var longPressed = false
        private val longPress = Runnable {
            longPressed = true
            v.performHapticFeedback(android.view.HapticFeedbackConstants.LONG_PRESS)
            showMenu()
        }

        override fun onTouch(view: View, e: MotionEvent): Boolean {
            when (e.actionMasked) {
                MotionEvent.ACTION_DOWN -> {
                    downX = e.rawX; downY = e.rawY
                    startX = p.x; startY = p.y
                    dragging = false; longPressed = false
                    handler.postDelayed(longPress, ViewConfiguration.getLongPressTimeout().toLong())
                }
                MotionEvent.ACTION_MOVE -> {
                    val dx = e.rawX - downX
                    val dy = e.rawY - downY
                    if (!dragging && (abs(dx) > slop || abs(dy) > slop)) {
                        dragging = true
                        handler.removeCallbacks(longPress)
                        dismissMenu()
                    }
                    if (dragging) {
                        p.x = (startX + dx).toInt().coerceAtLeast(0)
                        p.y = (startY + dy).toInt().coerceAtLeast(0)
                        runCatching { wm.updateViewLayout(v, p) }
                    }
                }
                MotionEvent.ACTION_UP, MotionEvent.ACTION_CANCEL -> {
                    handler.removeCallbacks(longPress)
                    if (dragging) {
                        snapToEdge()
                    } else if (!longPressed && e.actionMasked == MotionEvent.ACTION_UP) {
                        if (menu != null) dismissMenu() else listener.onBubbleTap()
                    }
                }
            }
            return true
        }

        private fun snapToEdge() {
            val w = context.resources.displayMetrics.widthPixels
            p.x = if (p.x + size / 2 < w / 2) 0 else w - size
            runCatching { wm.updateViewLayout(v, p) }
            prefs.bubbleX = p.x
            prefs.bubbleY = p.y
        }
    }

    @SuppressLint("ClickableViewAccessibility")
    private fun showMenu() {
        dismissMenu()
        val p0 = params ?: return
        val dm = context.resources.displayMetrics
        val pad = (14 * density).toInt()
        val box = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundResource(R.drawable.bubble_bg)
            setPadding(0, (6 * density).toInt(), 0, (6 * density).toInt())
            elevation = 8 * density
        }
        val items = listener.menuItems()
        val estH = ((items.size * 46 + 12) * density).toInt()
        for ((title, action) in items) {
            box.addView(TextView(context).apply {
                text = title
                textSize = 15f
                setTextColor(0xFFFFFFFF.toInt())
                setPadding(pad, pad * 2 / 3, pad, pad * 2 / 3)
                setOnClickListener { dismissMenu(); action() }
            })
        }
        val width = (260 * density).toInt().coerceAtMost(dm.widthPixels - (16 * density).toInt())
        val mp = WindowManager.LayoutParams(
            width, WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or WindowManager.LayoutParams.FLAG_WATCH_OUTSIDE_TOUCH,
            PixelFormat.TRANSLUCENT
        ).apply {
            gravity = Gravity.TOP or Gravity.START
            x = if (p0.x + size / 2 < dm.widthPixels / 2) p0.x + size else (p0.x - width).coerceAtLeast(0)
            y = (p0.y - (40 * density).toInt()).coerceAtMost(dm.heightPixels - estH).coerceAtLeast(0)
        }
        box.setOnTouchListener { _, e ->
            if (e.actionMasked == MotionEvent.ACTION_OUTSIDE) dismissMenu()
            false
        }
        wm.addView(box, mp)
        menu = box
    }

    fun dismissMenu() {
        menu?.let { runCatching { wm.removeView(it) } }
        menu = null
    }
}
