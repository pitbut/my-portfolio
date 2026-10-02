package ru.konstruktor.eskiz.ui

import android.graphics.Matrix
import android.graphics.Paint
import android.graphics.Path
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.foundation.gestures.calculateCentroid
import androidx.compose.foundation.gestures.calculatePan
import androidx.compose.foundation.gestures.calculateZoom
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.drawscope.drawIntoCanvas
import androidx.compose.ui.graphics.nativeCanvas
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.input.pointer.positionChange
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.unit.IntSize
import ru.konstruktor.eskiz.geom.DimLayout
import ru.konstruktor.eskiz.geom.P
import ru.konstruktor.eskiz.geom.dist
import ru.konstruktor.eskiz.render.CanvasPen
import ru.konstruktor.eskiz.render.Colors
import ru.konstruktor.eskiz.render.Renderer
import kotlin.math.max
import kotlin.math.min

private enum class Gesture { UNDECIDED, PLACE, DRAG_POINT, TRANSFORM }

/** Фото с разметкой: масштаб двумя пальцами, установка точек с лупой, перетаскивание точек. */
@Composable
fun PhotoCanvas(vm: EditorViewModel, modifier: Modifier = Modifier) {
    val bmp = vm.bitmap
    if (bmp == null) {
        Box(modifier.fillMaxSize(), contentAlignment = Alignment.Center) { CircularProgressIndicator() }
        return
    }
    val project = vm.project
    val density = LocalDensity.current.density
    val tolPx = 26f * density

    var size by remember { mutableStateOf(IntSize.Zero) }
    var zoom by remember { mutableFloatStateOf(0f) }
    var pan by remember { mutableStateOf(Offset.Zero) }
    var loupe by remember { mutableStateOf<P?>(null) }
    var finger by remember { mutableStateOf<Offset?>(null) }
    var rect by remember { mutableStateOf<Pair<Offset, Offset>?>(null) }
    val holder = remember { object { var layout: DimLayout.Result? = null } }

    fun fit() {
        if (size.width == 0) return
        zoom = min(size.width.toFloat() / project.imageW, size.height.toFloat() / project.imageH) * 0.96f
        pan = Offset((size.width - project.imageW * zoom) / 2, (size.height - project.imageH * zoom) / 2)
    }

    fun toImg(o: Offset) = P(((o.x - pan.x) / zoom).toDouble(), ((o.y - pan.y) / zoom).toDouble())
    fun toScreen(p: P) = P(p.x * zoom + pan.x, p.y * zoom + pan.y)
    fun tolImg() = (tolPx / zoom).toDouble()

    val bmpPaint = remember { Paint(Paint.FILTER_BITMAP_FLAG) }
    val loupeStroke = remember { Paint(Paint.ANTI_ALIAS_FLAG).apply { style = Paint.Style.STROKE } }

    Canvas(
        modifier
            .fillMaxSize()
            .onSizeChanged { size = it; if (zoom == 0f) fit() }
            .pointerInput(vm.tool) {
                awaitEachGesture {
                    val down = awaitFirstDown(requireUnconsumed = false)
                    val start = down.position
                    val tool = vm.tool
                    var kind = Gesture.UNDECIDED
                    var dragId: Int? = null
                    var dragOrigin = P(0.0, 0.0)
                    when (tool) {
                        Tool.SELECT -> vm.hitPoint(toImg(start), tolImg())?.let {
                            dragId = it; kind = Gesture.DRAG_POINT
                            dragOrigin = vm.project.point(it)!!.p
                            vm.startDrag()
                            loupe = dragOrigin; finger = start
                        }
                        Tool.POINT, Tool.LINE, Tool.ARC, Tool.DIM, Tool.CIRCLE -> {
                            kind = Gesture.PLACE
                            loupe = vm.snapTarget(toImg(start), tolImg()); finger = start
                        }
                        Tool.AUTO -> {}
                    }
                    var moved = false
                    var last = start
                    while (true) {
                        val ev = awaitPointerEvent()
                        val pressed = ev.changes.filter { it.pressed }
                        if (pressed.isEmpty()) break
                        if (pressed.size >= 2) {
                            if (kind == Gesture.DRAG_POINT) dragId?.let { vm.dragPoint(it, dragOrigin) }
                            kind = Gesture.TRANSFORM
                            loupe = null; finger = null; rect = null
                            val z = ev.calculateZoom()
                            val c = ev.calculateCentroid()
                            val pn = ev.calculatePan()
                            val nz = (zoom * z).coerceIn(0.05f, 40f)
                            pan = c - (c - pan) * (nz / zoom) + pn
                            zoom = nz
                            ev.changes.forEach { it.consume() }
                            continue
                        }
                        if (kind == Gesture.TRANSFORM) continue
                        val ch = pressed[0]
                        val pos = ch.position
                        if (!moved && (pos - start).getDistance() > viewConfiguration.touchSlop) moved = true
                        when (kind) {
                            Gesture.DRAG_POINT -> {
                                val id = dragId!!
                                val img = dragOrigin + P(((pos.x - start.x) / zoom).toDouble(), ((pos.y - start.y) / zoom).toDouble())
                                vm.dragPoint(id, img)
                                loupe = img; finger = pos
                            }
                            Gesture.PLACE -> { loupe = vm.snapTarget(toImg(pos), tolImg()); finger = pos }
                            Gesture.UNDECIDED -> if (moved) {
                                if (tool == Tool.AUTO) rect = start to pos
                                else pan += ch.positionChange()
                            }
                            Gesture.TRANSFORM -> {}
                        }
                        last = pos
                        ch.consume()
                    }
                    when (kind) {
                        Gesture.DRAG_POINT -> {
                            val id = dragId!!
                            vm.endDrag(id, vm.project.point(id)!!.p, tolImg())
                        }
                        Gesture.PLACE -> vm.place(toImg(last), tolImg())
                        Gesture.UNDECIDED -> {
                            if (tool == Tool.AUTO) {
                                val r = rect
                                if (r != null && (r.second - r.first).getDistance() > tolPx * 2) vm.autoContour(toImg(r.first) to toImg(r.second), null)
                                else if (!moved) vm.autoContour(null, toImg(start))
                            } else if (!moved && tool == Tool.SELECT) {
                                val l = holder.layout
                                val hit = l?.let { lay ->
                                    (lay.linear.map { it.id to it.textCenter } + lay.diameters.map { it.id to it.textCenter })
                                        .filter { dist(it.second, P(start.x.toDouble(), start.y.toDouble())) < tolPx * 1.4 }
                                        .minByOrNull { dist(it.second, P(start.x.toDouble(), start.y.toDouble())) }?.first
                                }
                                vm.tapSelect(toImg(start), tolImg(), hit)
                            }
                        }
                        Gesture.TRANSFORM -> {}
                    }
                    loupe = null; finger = null; rect = null
                }
            }
    ) {
        if (zoom == 0f) return@Canvas
        drawIntoCanvas { cc ->
            val c = cc.nativeCanvas
            c.drawColor(0xFF263238.toInt())
            val m = Matrix().apply {
                val s = zoom * project.imageW / bmp.width
                postScale(s, s); postTranslate(pan.x, pan.y)
            }
            c.drawBitmap(bmp, m, bmpPaint)

            val sel = vm.selection
            val visible = if (vm.stepMode) DrawingOrder.visible(vm.project, vm.stepCount) else null
            holder.layout = Renderer.drawPhotoOverlay(
                CanvasPen(c), vm.project, vm.calibration, ::toScreen, density,
                Renderer.PhotoOverlay(
                    selectedDim = (sel as? Selection.Dim)?.id,
                    selectedPoint = (sel as? Selection.Point)?.id,
                    selectedLine = (sel as? Selection.Line)?.id,
                    selectedCircle = (sel as? Selection.Circle)?.id,
                    selectedArc = (sel as? Selection.Arc)?.id,
                    pendingPoints = vm.pending.toSet(),
                    pendingCirclePts = vm.circlePts,
                    showDims = vm.showDims,
                    showLines = vm.showLines,
                    visible = visible,
                ),
            )

            rect?.let { (a, b) ->
                loupeStroke.color = Colors.SELECTED; loupeStroke.strokeWidth = 2f * density
                c.drawRect(min(a.x, b.x), min(a.y, b.y), max(a.x, b.x), max(a.y, b.y), loupeStroke)
            }

            // Лупа: увеличенный участок фото вокруг точки, над пальцем.
            val target = loupe
            val f = finger
            if (target != null && f != null) {
                val r = 58f * density
                var cy = f.y - r - 70f * density
                if (cy < r + 8 * density) cy = f.y + r + 70f * density
                val cx = f.x.coerceIn(r + 8 * density, size.width - r - 8 * density)
                val lz = max(zoom * 3f, 0.5f)
                c.save()
                val clip = Path().apply { addCircle(cx, cy, r, Path.Direction.CW) }
                c.clipPath(clip)
                c.drawColor(0xFF000000.toInt())
                val lm = Matrix().apply {
                    val s = lz * project.imageW / bmp.width
                    postScale(s, s)
                    postTranslate((cx - target.x * lz).toFloat(), (cy - target.y * lz).toFloat())
                }
                c.drawBitmap(bmp, lm, bmpPaint)
                loupeStroke.color = Colors.SELECTED; loupeStroke.strokeWidth = 1.5f * density
                c.drawLine(cx - r, cy, cx - 6 * density, cy, loupeStroke)
                c.drawLine(cx + 6 * density, cy, cx + r, cy, loupeStroke)
                c.drawLine(cx, cy - r, cx, cy - 6 * density, loupeStroke)
                c.drawLine(cx, cy + 6 * density, cx, cy + r, loupeStroke)
                c.restore()
                loupeStroke.color = 0xFFFFFFFF.toInt(); loupeStroke.strokeWidth = 3f * density
                c.drawCircle(cx, cy, r, loupeStroke)
            }
        }
    }
}
