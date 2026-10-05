package ru.konstruktor.eskiz.data

import android.content.Context
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import ru.konstruktor.eskiz.geom.Calibration
import ru.konstruktor.eskiz.geom.Calibrator
import ru.konstruktor.eskiz.geom.Constraint
import ru.konstruktor.eskiz.geom.DiameterConstraint
import ru.konstruktor.eskiz.geom.LinearConstraint
import ru.konstruktor.eskiz.geom.Mat3
import ru.konstruktor.eskiz.geom.RadiusConstraint
import java.io.File
import java.util.UUID

/** Вид 3D-модели: какой эскиз и с какой стороны. [role] — имя из MultiView.Role. */
@Serializable
data class ViewRef(val projectId: String, val role: String, val mirror: Boolean = false)

/** 3D-модель, собранная из эскизов видов (спереди, сверху, слева/справа). */
@Serializable
data class Model3D(
    val id: String,
    val name: String,
    val created: Long,
    val updated: Long,
    val views: List<ViewRef> = emptyList(),
    /** Толщина, если вид один, мм. */
    val thickness: Double? = null,
)

/** 3D-модели хранятся в памяти телефона: models/<id>.json. */
class ModelStore(context: Context) {
    private val json = Json { ignoreUnknownKeys = true; encodeDefaults = true }
    private val root = File(context.filesDir, "models").apply { mkdirs() }

    fun list(): List<Model3D> = root.listFiles().orEmpty().filter { it.extension == "json" }
        .mapNotNull { runCatching { json.decodeFromString(Model3D.serializer(), it.readText()) }.getOrNull() }
        .sortedByDescending { it.updated }

    fun load(id: String): Model3D = json.decodeFromString(Model3D.serializer(), File(root, "$id.json").readText())

    fun save(m: Model3D) {
        val tmp = File(root, "${m.id}.json.tmp")
        tmp.writeText(json.encodeToString(Model3D.serializer(), m))
        tmp.renameTo(File(root, "${m.id}.json"))
    }

    fun delete(id: String) { File(root, "$id.json").delete() }

    fun create(name: String): Model3D {
        val now = System.currentTimeMillis()
        return Model3D(UUID.randomUUID().toString(), name, now, now).also(::save)
    }
}

/** Калибровка эскиза по всем введённым размерам (и листу-мишени, если найден). */
fun calibrationOf(p: Project): Calibration {
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
    for (a in p.arcs) {
        val k = a.known ?: continue
        val pa = p.point(a.a) ?: continue
        val pm = p.point(a.m) ?: continue
        val pb = p.point(a.b) ?: continue
        cs += RadiusConstraint(a.id, pa.p, pm.p, pb.p, k)
    }
    val sheet = p.sheetH?.let { Mat3(it.toDoubleArray()) }
    return Calibrator.calibrate(p.imageW, p.imageH, sheet, cs)
}
