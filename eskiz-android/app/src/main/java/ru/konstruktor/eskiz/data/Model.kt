package ru.konstruktor.eskiz.data

import kotlinx.serialization.Serializable
import ru.konstruktor.eskiz.geom.P

@Serializable
data class SPoint(val id: Int, val x: Double, val y: Double) {
    val p get() = P(x, y)
}

/** Линия контура между двумя точками. */
@Serializable
data class SLine(val id: Int, val a: Int, val b: Int)

/**
 * Линейный размер между двумя точками. [known] — введённое значение, null — вычисляется.
 * [onDrawing] — показывать на чертеже (null — решается автоматически).
 */
@Serializable
data class SDim(val id: Int, val a: Int, val b: Int, val known: Double? = null, val onDrawing: Boolean? = null)

/** Окружность (отверстие) по точкам на её краю в координатах фото. */
@Serializable
data class SCircle(val id: Int, val pts: List<P>, val known: Double? = null)

/** Дуга контура через три точки: начало [a], точка на дуге [m], конец [b]. [known] — радиус. */
@Serializable
data class SArc(val id: Int, val a: Int, val m: Int, val b: Int, val known: Double? = null)

@Serializable
data class Stamp(
    val title: String = "",
    val author: String = "",
    val material: String = "",
)

@Serializable
data class Project(
    val id: String,
    val name: String,
    val created: Long,
    val updated: Long,
    val imageW: Int,
    val imageH: Int,
    val points: List<SPoint> = emptyList(),
    val lines: List<SLine> = emptyList(),
    val dims: List<SDim> = emptyList(),
    val circles: List<SCircle> = emptyList(),
    val arcs: List<SArc> = emptyList(),
    val nextId: Int = 1,
    /** Гомография листа-мишени (пиксели → мм), построчно 9 чисел. */
    val sheetH: List<Double>? = null,
    /** Дополнительный поворот чертежа, шаги по 90°. */
    val rotationSteps: Int = 0,
    val stamp: Stamp = Stamp(),
    /** Толщина детали для 3D-модели, мм. */
    val thickness: Double? = null,
) {
    fun point(id: Int) = points.firstOrNull { it.id == id }
}
