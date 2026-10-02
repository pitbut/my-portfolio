package ru.konstruktor.eskiz.ui

import android.app.Application
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import ru.konstruktor.eskiz.cv.Vision
import ru.konstruktor.eskiz.data.Project
import ru.konstruktor.eskiz.data.ProjectStore
import ru.konstruktor.eskiz.data.SCircle
import ru.konstruktor.eskiz.data.SDim
import ru.konstruktor.eskiz.data.SLine
import ru.konstruktor.eskiz.data.SPoint
import ru.konstruktor.eskiz.data.Stamp
import ru.konstruktor.eskiz.export.Exporters
import ru.konstruktor.eskiz.geom.Calibration
import ru.konstruktor.eskiz.geom.Calibrator
import ru.konstruktor.eskiz.geom.Constraint
import ru.konstruktor.eskiz.geom.DiameterConstraint
import ru.konstruktor.eskiz.geom.LinearConstraint
import ru.konstruktor.eskiz.geom.Mat3
import ru.konstruktor.eskiz.geom.P
import ru.konstruktor.eskiz.geom.dist
import ru.konstruktor.eskiz.geom.distToSegment
import ru.konstruktor.eskiz.render.Values
import java.io.File
import kotlin.math.max

enum class Tool(val title: String) {
    SELECT("Выбор"), POINT("Точка"), LINE("Линия"), DIM("Размер"), CIRCLE("Отверстие"), AUTO("Авто"),
}

enum class ViewMode { PHOTO, DRAWING }

sealed interface Selection {
    data class Point(val id: Int) : Selection
    data class Line(val id: Int) : Selection
    data class Dim(val id: Int) : Selection
    data class Circle(val id: Int) : Selection
}

/** Окно ввода размера: для линейного размера (a, b) или для окружности. */
data class DimDialog(val a: Int = 0, val b: Int = 0, val dimId: Int? = null, val circleId: Int? = null)

enum class ExportKind { DRAWING_PNG, PHOTO, PDF, DXF, ALL }

class EditorViewModel(app: Application, projectId: String) : AndroidViewModel(app) {
    private val store = ProjectStore(app)

    var project by mutableStateOf(store.load(projectId)); private set
    var calibration by mutableStateOf(Calibration.NONE); private set
    var bitmap by mutableStateOf<Bitmap?>(null); private set
    var corners: List<P> = emptyList(); private set

    var tool by mutableStateOf(Tool.SELECT)
    var mode by mutableStateOf(ViewMode.PHOTO)
    var selection by mutableStateOf<Selection?>(null)
    var pending by mutableStateOf<List<Int>>(emptyList()); private set
    var circlePts by mutableStateOf<List<P>>(emptyList()); private set
    var dialog by mutableStateOf<DimDialog?>(null)
    var busy by mutableStateOf<String?>(null); private set
    var message by mutableStateOf<String?>(null)
    var stepMode by mutableStateOf(false)
    var stepCount by mutableStateOf(0)
    var showDims by mutableStateOf(true)
    var showLines by mutableStateOf(true)

    private val undoStack = ArrayDeque<Project>()
    var canUndo by mutableStateOf(false); private set

    val photoFile: File get() = store.photo(project.id)

    private var calibJob: Job? = null
    private var saveJob: Job? = null

    init {
        viewModelScope.launch {
            val bmp = withContext(Dispatchers.IO) {
                val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
                BitmapFactory.decodeFile(photoFile.absolutePath, bounds)
                var sample = 1
                while (max(bounds.outWidth, bounds.outHeight) / (sample * 2) >= 2048) sample *= 2
                BitmapFactory.decodeFile(photoFile.absolutePath, BitmapFactory.Options().apply { inSampleSize = sample })
            }
            bitmap = bmp
            corners = withContext(Dispatchers.Default) { runCatching { Vision.detectCorners(photoFile.absolutePath) }.getOrDefault(emptyList()) }
        }
        recalibrate()
    }

    // ---------- Изменение проекта ----------

    private fun update(snapshot: Boolean = true, f: (Project) -> Project) {
        if (snapshot) {
            undoStack.addLast(project)
            if (undoStack.size > 100) undoStack.removeFirst()
            canUndo = true
        }
        val old = project
        project = f(project).copy(updated = System.currentTimeMillis())
        if (old.points != project.points || old.dims != project.dims || old.circles != project.circles || old.sheetH != project.sheetH) {
            recalibrate()
        }
        scheduleSave()
    }

    fun undo() {
        val prev = undoStack.removeLastOrNull() ?: return
        canUndo = undoStack.isNotEmpty()
        project = prev
        selection = null; pending = emptyList(); circlePts = emptyList()
        recalibrate(); scheduleSave()
    }

    private fun scheduleSave() {
        saveJob?.cancel()
        val p = project
        saveJob = viewModelScope.launch(Dispatchers.IO) { delay(400); store.save(p) }
    }

    fun saveNow() { val p = project; viewModelScope.launch(Dispatchers.IO) { store.save(p) } }

    private fun recalibrate() {
        calibJob?.cancel()
        val p = project
        calibJob = viewModelScope.launch {
            val cal = withContext(Dispatchers.Default) {
                val cs = ArrayList<Constraint>()
                for (d in p.dims) {
                    val k = d.known ?: continue
                    val a = p.point(d.a) ?: continue
                    val b = p.point(d.b) ?: continue
                    cs += LinearConstraint(d.id, a.p, b.p, k)
                }
                for (c in p.circles) {
                    val k = c.known ?: continue
                    if (c.pts.size >= 3) cs += DiameterConstraint(c.id, c.pts, k)
                }
                val sheet = p.sheetH?.let { Mat3(it.toDoubleArray()) }
                Calibrator.calibrate(p.imageW, p.imageH, sheet, cs)
            }
            calibration = cal
        }
    }

    private fun newId(p: Project) = p.nextId

    // ---------- Поиск объектов ----------

    fun hitPoint(img: P, tol: Double): Int? =
        project.points.filter { dist(it.p, img) <= tol }.minByOrNull { dist(it.p, img) }?.id

    private fun hitLine(img: P, tol: Double): Int? = project.lines.mapNotNull { l ->
        val a = project.point(l.a) ?: return@mapNotNull null
        val b = project.point(l.b) ?: return@mapNotNull null
        val d = distToSegment(img, a.p, b.p)
        if (d <= tol) l.id to d else null
    }.minByOrNull { it.second }?.first

    private fun hitCircle(img: P, tol: Double): Int? = project.circles.mapNotNull { c ->
        val fc = ru.konstruktor.eskiz.geom.fitCircle(c.pts) ?: return@mapNotNull null
        val d = kotlin.math.abs(dist(fc.c, img) - fc.r)
        if (d <= tol || dist(fc.c, img) < fc.r * 0.5) c.id to d else null
    }.minByOrNull { it.second }?.first

    /** Куда встанет точка: на существующую точку, на угол или туда, где палец. */
    fun snapTarget(img: P, tol: Double): P {
        hitPoint(img, tol)?.let { return project.point(it)!!.p }
        if (tool == Tool.CIRCLE) return img
        val c = corners.minByOrNull { dist(it, img) }
        return if (c != null && dist(c, img) <= tol * 0.7) c else img
    }

    // ---------- Действия инструментов ----------

    /** Касание без перемещения в режиме «Выбор». [dimHit] — размер, по тексту которого попали. */
    fun tapSelect(img: P, tol: Double, dimHit: Int?) {
        selection = when {
            dimHit != null -> Selection.Dim(dimHit)
            else -> hitPoint(img, tol)?.let { Selection.Point(it) }
                ?: hitLine(img, tol)?.let { Selection.Line(it) }
                ?: hitCircle(img, tol)?.let { Selection.Circle(it) }
        }
    }

    /** Отпускание пальца в режимах установки точек. */
    fun place(img: P, tol: Double) {
        when (tool) {
            Tool.POINT -> { obtainPoint(img, tol) }
            Tool.LINE -> {
                val id = obtainPoint(img, tol)
                val last = pending.lastOrNull()
                if (last == null) pending = listOf(id)
                else if (last == id) { pending = emptyList(); message = "Линия завершена" }
                else {
                    if (project.lines.none { (it.a == last && it.b == id) || (it.a == id && it.b == last) }) {
                        update { p -> p.copy(lines = p.lines + SLine(newId(p), last, id), nextId = p.nextId + 1) }
                    }
                    pending = listOf(id)
                }
            }
            Tool.DIM -> {
                val first = pending.firstOrNull()
                val onPoint = hitPoint(img, tol)
                if (first == null && onPoint == null) {
                    // Касание по линии контура — размер этой линии.
                    hitLine(img, tol)?.let { lid ->
                        val l = project.lines.first { it.id == lid }
                        dialog = DimDialog(l.a, l.b)
                        return
                    }
                }
                val id = obtainPoint(img, tol)
                if (first == null) pending = listOf(id)
                else if (first != id) { dialog = DimDialog(first, id); pending = emptyList() }
            }
            Tool.CIRCLE -> {
                val pts = circlePts + img
                if (pts.size >= 3) {
                    circlePts = emptyList()
                    var cid = 0
                    update { p -> cid = newId(p); p.copy(circles = p.circles + SCircle(cid, pts), nextId = p.nextId + 1) }
                    dialog = DimDialog(circleId = cid)
                } else circlePts = pts
            }
            else -> {}
        }
    }

    private fun obtainPoint(img: P, tol: Double): Int {
        hitPoint(img, tol)?.let { return it }
        val t = snapTarget(img, tol)
        var id = 0
        update { p -> id = newId(p); p.copy(points = p.points + SPoint(id, t.x, t.y), nextId = p.nextId + 1) }
        return id
    }

    private var dragStart: Project? = null

    fun startDrag() { dragStart = project }

    fun dragPoint(id: Int, img: P) {
        update(snapshot = false) { p -> p.copy(points = p.points.map { if (it.id == id) it.copy(x = img.x, y = img.y) else it }) }
    }

    fun endDrag(id: Int, img: P, tol: Double) {
        // При отпускании — привязка к углу (не к самой себе).
        val c = corners.minByOrNull { dist(it, img) }
        val t = if (c != null && dist(c, img) <= tol * 0.7) c else img
        dragPoint(id, t)
        dragStart?.let { if (it != project) { undoStack.addLast(it); canUndo = true } }
        dragStart = null
    }

    fun cancelPending() { pending = emptyList(); circlePts = emptyList() }

    fun saveDim(d: DimDialog, value: Double?) {
        dialog = null
        when {
            d.circleId != null -> update { p -> p.copy(circles = p.circles.map { if (it.id == d.circleId) it.copy(known = value) else it }) }
            d.dimId != null -> update { p -> p.copy(dims = p.dims.map { if (it.id == d.dimId) it.copy(known = value) else it }) }
            else -> {
                val existing = project.dims.firstOrNull { (it.a == d.a && it.b == d.b) || (it.a == d.b && it.b == d.a) }
                if (existing != null) update { p -> p.copy(dims = p.dims.map { if (it.id == existing.id) it.copy(known = value) else it }) }
                else update { p -> p.copy(dims = p.dims + SDim(newId(p), d.a, d.b, value), nextId = p.nextId + 1) }
            }
        }
    }

    fun deleteSelection() {
        when (val s = selection) {
            is Selection.Point -> update { p ->
                p.copy(points = p.points.filter { it.id != s.id },
                    lines = p.lines.filter { it.a != s.id && it.b != s.id },
                    dims = p.dims.filter { it.a != s.id && it.b != s.id })
            }
            is Selection.Line -> update { p -> p.copy(lines = p.lines.filter { it.id != s.id }) }
            is Selection.Dim -> update { p -> p.copy(dims = p.dims.filter { it.id != s.id }) }
            is Selection.Circle -> update { p -> p.copy(circles = p.circles.filter { it.id != s.id }) }
            null -> {}
        }
        selection = null
    }

    fun editSelection() {
        dialog = when (val s = selection) {
            is Selection.Dim -> project.dims.firstOrNull { it.id == s.id }?.let { DimDialog(it.a, it.b, dimId = it.id) }
            is Selection.Circle -> DimDialog(circleId = s.id)
            is Selection.Line -> project.lines.firstOrNull { it.id == s.id }?.let { DimDialog(it.a, it.b) }
            else -> null
        }
    }

    fun isOnDrawing(id: Int): Boolean {
        val d = project.dims.firstOrNull { it.id == id } ?: return false
        return ru.konstruktor.eskiz.render.DrawingModel(project, calibration).shown(d)
    }

    fun toggleOnDrawing(id: Int) {
        val now = isOnDrawing(id)
        update { p -> p.copy(dims = p.dims.map { if (it.id == id) it.copy(onDrawing = !now) else it }) }
    }

    fun clearAll() {
        update { p -> p.copy(points = emptyList(), lines = emptyList(), dims = emptyList(), circles = emptyList(), nextId = 1) }
        selection = null; cancelPending()
    }

    // ---------- Автоматика ----------

    fun autoContour(rect: Pair<P, P>?, tap: P?) {
        if (busy != null) return
        busy = "Ищу контур детали…"
        viewModelScope.launch {
            val res = withContext(Dispatchers.Default) {
                runCatching { Vision.autoContour(photoFile.absolutePath, rect, tap, corners) }.getOrNull()
            }
            busy = null
            if (res == null || res.outline.size < 3) {
                message = "Контур не найден. Обведите деталь рамкой или положите её на контрастный фон."
                return@launch
            }
            update { p0 ->
                var p = p0
                val tol = max(p.imageW, p.imageH) * 0.004
                fun pointAt(pt: P): Int {
                    p.points.firstOrNull { dist(it.p, pt) <= tol }?.let { return it.id }
                    val id = p.nextId
                    p = p.copy(points = p.points + SPoint(id, pt.x, pt.y), nextId = id + 1)
                    return id
                }
                fun poly(pts: List<P>) {
                    val ids = pts.map { pointAt(it) }
                    for (i in ids.indices) {
                        val a = ids[i]; val b = ids[(i + 1) % ids.size]
                        if (a != b && p.lines.none { (it.a == a && it.b == b) || (it.a == b && it.b == a) }) {
                            p = p.copy(lines = p.lines + SLine(p.nextId, a, b), nextId = p.nextId + 1)
                        }
                    }
                }
                poly(res.outline)
                res.cutouts.forEach { poly(it) }
                for (h in res.holes) p = p.copy(circles = p.circles + SCircle(p.nextId, h), nextId = p.nextId + 1)
                p
            }
            message = "Найдено: контур ${res.outline.size} верш., отверстий ${res.holes.size}" +
                if (res.cutouts.isNotEmpty()) ", вырезов ${res.cutouts.size}" else ""
            tool = Tool.DIM
        }
    }

    fun detectSheet() {
        if (busy != null) return
        busy = "Ищу лист-мишень…"
        viewModelScope.launch {
            val r = withContext(Dispatchers.Default) { runCatching { Vision.detectSheet(photoFile.absolutePath) }.getOrNull() }
            busy = null
            if (r == null) {
                message = "Метки листа-мишени не найдены"
            } else {
                update { p -> p.copy(sheetH = r.first.m.toList()) }
                message = "Лист-мишень найден: меток ${r.second} из 4" + if (r.second < 2) ". Для точности нужно минимум 2." else ""
            }
        }
    }

    fun removeSheet() = update { p -> p.copy(sheetH = null) }

    // ---------- Прочее ----------

    fun rename(name: String) = update { p -> p.copy(name = name.ifBlank { p.name }) }
    fun setStamp(s: Stamp) = update { p -> p.copy(stamp = s) }
    fun rotateDrawing() = update { p -> p.copy(rotationSteps = (p.rotationSteps + 1) % 4) }

    fun values() = Values(project, calibration)

    /** Готовит файлы для отправки (в фоне) и отдаёт их в [onReady]. */
    fun export(kind: ExportKind, onReady: (List<File>) -> Unit) {
        if (busy != null) return
        busy = "Готовлю файлы…"
        val p = project; val cal = calibration; val ctx = getApplication<Application>()
        viewModelScope.launch {
            val files = withContext(Dispatchers.Default) {
                runCatching {
                    when (kind) {
                        ExportKind.DRAWING_PNG -> listOf(Exporters.drawingPng(ctx, p, cal))
                        ExportKind.PHOTO -> listOf(Exporters.photoJpg(ctx, p, cal, photoFile))
                        ExportKind.PDF -> listOf(Exporters.drawingPdf(ctx, p, cal))
                        ExportKind.DXF -> listOf(Exporters.drawingDxf(ctx, p, cal))
                        ExportKind.ALL -> listOf(
                            Exporters.drawingPng(ctx, p, cal), Exporters.photoJpg(ctx, p, cal, photoFile),
                            Exporters.drawingPdf(ctx, p, cal), Exporters.drawingDxf(ctx, p, cal),
                        )
                    }
                }
            }
            busy = null
            files.onSuccess(onReady).onFailure { message = "Не удалось подготовить файл: ${it.message}" }
        }
    }

    override fun onCleared() {
        store.save(project)
        super.onCleared()
    }
}
