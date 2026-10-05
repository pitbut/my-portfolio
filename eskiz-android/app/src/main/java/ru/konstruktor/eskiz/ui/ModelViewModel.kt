package ru.konstruktor.eskiz.ui

import android.app.Application
import android.graphics.Bitmap
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import ru.konstruktor.eskiz.data.Model3D
import ru.konstruktor.eskiz.data.ModelStore
import ru.konstruktor.eskiz.data.Project
import ru.konstruktor.eskiz.data.ProjectStore
import ru.konstruktor.eskiz.data.ViewRef
import ru.konstruktor.eskiz.data.calibrationOf
import ru.konstruktor.eskiz.export.Exporters
import ru.konstruktor.eskiz.export.Extrusion
import ru.konstruktor.eskiz.export.SolidExport
import ru.konstruktor.eskiz.geom3d.MultiView
import ru.konstruktor.eskiz.geom3d.Preview
import ru.konstruktor.eskiz.render.DrawingModel
import java.io.File

enum class Model3DExport(val title: String) {
    STEP("3D-модель STEP (КОМПАС, SolidWorks, FreeCAD, Fusion)"),
    STL("STL (3D-печать, просмотрщики)"),
}

class ModelViewModel(app: Application, modelId: String) : AndroidViewModel(app) {
    private val models = ModelStore(app)
    val projects = ProjectStore(app)

    var model by mutableStateOf(models.load(modelId)); private set
    var sketches by mutableStateOf<List<Project>>(emptyList()); private set

    /** Результат сборки: тело, ошибки по видам или общая ошибка. */
    var result by mutableStateOf<MultiView.Result?>(null); private set
    var viewErrors by mutableStateOf<Map<MultiView.Role, String>>(emptyMap()); private set
    var error by mutableStateOf<String?>(null); private set
    var building by mutableStateOf(false); private set
    var busy by mutableStateOf<String?>(null); private set
    var message by mutableStateOf<String?>(null)

    private var singleProfile: Extrusion.Profile? = null
    private var buildJob: Job? = null

    init {
        viewModelScope.launch { sketches = withContext(Dispatchers.IO) { projects.list() } }
        rebuild()
    }

    fun refreshSketches() {
        viewModelScope.launch { sketches = withContext(Dispatchers.IO) { projects.list() } }
        rebuild()
    }

    private fun update(f: (Model3D) -> Model3D) {
        model = f(model).copy(updated = System.currentTimeMillis())
        val m = model
        viewModelScope.launch(Dispatchers.IO) { models.save(m) }
    }

    fun viewOf(role: MultiView.Role) = model.views.firstOrNull { it.role == role.name }

    fun setView(role: MultiView.Role, projectId: String?) {
        update { m ->
            val rest = m.views.filter { it.role != role.name }
            m.copy(views = if (projectId == null) rest else rest + ViewRef(projectId, role.name))
        }
        rebuild()
    }

    fun toggleMirror(role: MultiView.Role) {
        update { m -> m.copy(views = m.views.map { if (it.role == role.name) it.copy(mirror = !it.mirror) else it }) }
        rebuild()
    }

    fun setThickness(t: Double?) { update { it.copy(thickness = t) }; rebuild() }
    fun rename(name: String) = update { it.copy(name = name.ifBlank { it.name }) }

    fun rebuild() {
        buildJob?.cancel()
        val m = model
        building = true
        buildJob = viewModelScope.launch {
            val (res, errs, err, single) = withContext(Dispatchers.Default) { build(m) }
            result = res; viewErrors = errs; error = err; singleProfile = single
            building = false
        }
    }

    private data class Built(
        val result: MultiView.Result?, val viewErrors: Map<MultiView.Role, String>, val error: String?, val single: Extrusion.Profile?,
    )

    private fun build(m: Model3D): Built {
        if (m.views.isEmpty()) return Built(null, emptyMap(), null, null)
        val errs = HashMap<MultiView.Role, String>()
        val views = ArrayList<MultiView.View>()
        for (ref in m.views) {
            val role = runCatching { MultiView.Role.valueOf(ref.role) }.getOrNull() ?: continue
            val p = runCatching { projects.load(ref.projectId) }.getOrNull()
            if (p == null) { errs[role] = "Эскиз удалён"; continue }
            val cal = calibrationOf(p)
            if (!cal.calibrated) { errs[role] = "В эскизе нет масштаба — введите хотя бы один размер"; continue }
            try {
                views += MultiView.View(role, Extrusion.profile(DrawingModel(p, cal)), ref.mirror)
            } catch (e: Extrusion.ProfileError) {
                errs[role] = e.message ?: "Контур не подходит"
            }
        }
        if (errs.isNotEmpty()) return Built(null, errs, null, null)
        return try {
            val r = MultiView.build(views, m.thickness)
            Built(r, emptyMap(), null, if (views.size == 1) views[0].profile else null)
        } catch (e: MultiView.BuildError) {
            Built(null, emptyMap(), e.message, null)
        } catch (e: Exception) {
            Built(null, emptyMap(), "Не удалось построить модель: ${e.message}", null)
        }
    }

    /** Картинка модели для предпросмотра. */
    fun render(w: Int, h: Int, yaw: Double, pitch: Double): Bitmap? {
        val r = result ?: return null
        if (w <= 0 || h <= 0) return null
        val px = Preview.render(r.solid, w, h, yaw, pitch)
        return Bitmap.createBitmap(px, w, h, Bitmap.Config.ARGB_8888)
    }

    fun export(kind: Model3DExport, onReady: (File) -> Unit) {
        val r = result ?: return
        if (busy != null) return
        busy = "Готовлю файл…"
        val ctx = getApplication<Application>()
        val m = model
        val single = singleProfile
        viewModelScope.launch {
            val f = withContext(Dispatchers.Default) {
                runCatching {
                    val dir = File(ctx.cacheDir, "share").apply { mkdirs() }
                    val base = m.name.replace(Regex("[^\\p{L}\\p{N}_ -]"), "_").trim().ifBlank { "model" }
                    when (kind) {
                        Model3DExport.STEP -> File(dir, "$base.step").apply {
                            // Один вид — точная модель с настоящими дугами и цилиндрами, несколько — из плоских граней.
                            val text = if (single != null && m.thickness != null) Extrusion.step(single, m.thickness, m.name)
                            else SolidExport.step(r.solid, m.name)
                            writeText(text, Charsets.US_ASCII)
                        }
                        Model3DExport.STL -> File(dir, "$base.stl").apply { writeBytes(SolidExport.stl(r.solid, m.name)) }
                    }
                }
            }
            busy = null
            f.onSuccess(onReady).onFailure { message = "Не удалось подготовить файл: ${it.message}" }
        }
    }

    fun saveFile(file: File, uri: android.net.Uri) {
        val ctx = getApplication<Application>()
        viewModelScope.launch {
            val r = withContext(Dispatchers.IO) { runCatching { Exporters.saveTo(ctx, file, uri) } }
            message = if (r.isSuccess) "Сохранено: ${file.name}" else "Не удалось сохранить: ${r.exceptionOrNull()?.message}"
        }
    }
}
