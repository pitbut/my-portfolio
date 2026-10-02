package ru.konstruktor.eskiz.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.gestures.detectTransformGestures
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.drawscope.drawIntoCanvas
import androidx.compose.ui.graphics.nativeCanvas
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.unit.IntSize
import ru.konstruktor.eskiz.data.Project
import ru.konstruktor.eskiz.render.CanvasPen
import ru.konstruktor.eskiz.render.DrawingModel
import ru.konstruktor.eskiz.render.PageSpec
import ru.konstruktor.eskiz.render.Renderer
import kotlin.math.min

object DrawingOrder {
    /** Первые [n] размеров в порядке ввода — для пошагового показа. */
    fun visible(p: Project, n: Int): Set<Int> = all(p).take(n).toSet()
    fun all(p: Project): List<Int> = (p.dims.map { it.id } + p.circles.map { it.id } + p.arcs.map { it.id }).sorted()
}

/** Чистый чертёж на листе A4 — так же, как он уйдёт в PNG/PDF. */
@Composable
fun DrawingCanvas(vm: EditorViewModel, modifier: Modifier = Modifier) {
    val model = remember(vm.project, vm.calibration) { DrawingModel(vm.project, vm.calibration) }
    val page = remember(model) { PageSpec.choose(model.bounds) }
    var size by remember { mutableStateOf(IntSize.Zero) }
    var k by remember { mutableFloatStateOf(0f) }
    var pan by remember { mutableStateOf(Offset.Zero) }

    fun fit() {
        if (size.width == 0) return
        k = min(size.width / page.w.toFloat(), size.height / page.h.toFloat()) * 0.95f
        pan = Offset((size.width - page.w.toFloat() * k) / 2, (size.height - page.h.toFloat() * k) / 2)
    }
    LaunchedEffect(page.w, page.h, size) { fit() }

    Canvas(
        modifier
            .fillMaxSize()
            .onSizeChanged { size = it }
            .pointerInput(Unit) {
                detectTransformGestures { c, p, z, _ ->
                    val nk = (k * z).coerceIn(0.5f, 80f)
                    pan = c - (c - pan) * (nk / k) + p
                    k = nk
                }
            }
    ) {
        if (k == 0f) return@Canvas
        drawIntoCanvas { cc ->
            val c = cc.nativeCanvas
            c.drawColor(0xFF90A4AE.toInt())
            val visible = if (vm.stepMode) DrawingOrder.visible(vm.project, vm.stepCount) else null
            Renderer.drawPage(CanvasPen(c), model, page, k, pan.x, pan.y, visible)
        }
    }
}
