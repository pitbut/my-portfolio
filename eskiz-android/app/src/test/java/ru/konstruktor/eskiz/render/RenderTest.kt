package ru.konstruktor.eskiz.render

import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.RuntimeEnvironment
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode
import ru.konstruktor.eskiz.data.Project
import ru.konstruktor.eskiz.data.SCircle
import ru.konstruktor.eskiz.data.SDim
import ru.konstruktor.eskiz.data.SLine
import ru.konstruktor.eskiz.data.SPoint
import ru.konstruktor.eskiz.data.Stamp
import ru.konstruktor.eskiz.export.Exporters
import ru.konstruktor.eskiz.geom.Calibrator
import ru.konstruktor.eskiz.geom.LinearConstraint
import ru.konstruktor.eskiz.geom.Mat3
import ru.konstruktor.eskiz.geom.P
import ru.konstruktor.eskiz.geom.dist
import java.io.File
import kotlin.math.cos
import kotlin.math.sin

/** Рисует чертёж и фото с размерами в PNG (build/render-test) для визуальной проверки. */
@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(sdk = [34])
class RenderTest {
    private val w2p = Mat3(doubleArrayOf(9.0, 1.2, 700.0, -0.8, 8.0, 260.0, 0.0011, 0.0006, 1.0))
    private val plate = listOf(P(40.0, 70.0), P(170.0, 70.0), P(170.0, 150.0), P(110.0, 150.0), P(110.0, 220.0), P(40.0, 220.0))
    private val out = File("build/render-test").apply { mkdirs() }

    private fun project(): Project {
        val pts = plate.mapIndexed { i, p -> val q = w2p.apply(p); SPoint(i + 1, q.x, q.y) }
        val lines = (0 until 6).map { SLine(10 + it, it + 1, (it + 1) % 6 + 1) }
        // Введены 3 стороны и 2 диагонали, ещё 3 размера — вычисляемые.
        fun k(a: Int, b: Int) = dist(plate[a - 1], plate[b - 1])
        val dims = listOf(
            SDim(20, 1, 2, k(1, 2)), SDim(21, 2, 3, k(2, 3)), SDim(22, 6, 1, k(6, 1)),
            SDim(23, 1, 3, k(1, 3)), SDim(24, 2, 6, k(2, 6)), SDim(25, 4, 3, null),
            SDim(26, 5, 4, null), SDim(27, 6, 5, null),
        )
        fun circ(id: Int, c: P, r: Double, known: Double?) =
            SCircle(id, (0 until 16).map { w2p.apply(P(c.x + r * cos(it * Math.PI / 8), c.y + r * sin(it * Math.PI / 8))) }, known)
        val circles = listOf(circ(30, P(70.0, 110.0), 8.0, 16.0), circ(31, P(140.0, 105.0), 6.0, null), circ(32, P(75.0, 190.0), 10.0, null))
        return Project("t", "Пластина", 0, 1_700_000_000_000, 3000, 2250, pts, lines, dims, circles, 40,
            stamp = Stamp("Пластина опорная", "Иванов", "Ст3 s4"))
    }

    private fun cal(p: Project) = Calibrator.calibrate(p.imageW, p.imageH, null, p.dims.mapNotNull { d ->
        d.known?.let { LinearConstraint(d.id, p.point(d.a)!!.p, p.point(d.b)!!.p, it) }
    })

    @Test
    fun drawingPage() {
        val p = project(); val c = cal(p)
        val model = DrawingModel(p, c)
        val page = PageSpec.choose(model.bounds)
        val v = Values(p, c)
        for (id in listOf(25, 26, 27)) println("размер $id = ${v.computedDim(id)} ± ${v.dimUncertainty(id)}")
        for (id in listOf(31, 32)) println("Ø $id = ${v.computedCircle(id)} ± ${v.circleUncertainty(id)}")
        println("масштаб ${scaleLabel(page.scale)}, лист ${page.w}×${page.h}, режим ${c.mode}, ±${c.sigmaRel}")
        val k = 5f
        val bmp = Bitmap.createBitmap((page.w * k).toInt(), (page.h * k).toInt(), Bitmap.Config.ARGB_8888)
        Renderer.drawPage(Canvas(bmp), model, page, k, 0f, 0f)
        File(out, "page.png").outputStream().use { bmp.compress(Bitmap.CompressFormat.PNG, 100, it) }
        // Вычисленные размеры совпадают с истинными.
        assertTrue(kotlin.math.abs(v.computedDim(25)!! - 60.0) < 0.3)
        assertTrue(kotlin.math.abs(v.computedCircle(32)!! - 20.0) < 0.3)
    }

    @Test
    fun photoOverlay() {
        val p = project(); val c = cal(p)
        val s = 0.4
        val bmp = Bitmap.createBitmap((p.imageW * s).toInt(), (p.imageH * s).toInt(), Bitmap.Config.ARGB_8888)
        val cv = Canvas(bmp)
        cv.drawColor(Color.rgb(130, 95, 60))
        Renderer.drawPhotoOverlay(cv, p, c, { it * s }, 1.6f, Renderer.PhotoOverlay(selectedDim = 26))
        File(out, "photo.png").outputStream().use { bmp.compress(Bitmap.CompressFormat.PNG, 100, it) }
    }

    @Test
    fun dxf() {
        val p = project()
        val f = Exporters.drawingDxf(RuntimeEnvironment.getApplication(), p, cal(p))
        val txt = f.readText()
        f.copyTo(File(out, "plate.dxf"), overwrite = true)
        assertTrue(txt.startsWith("0\nSECTION"))
        assertTrue(txt.trimEnd().endsWith("EOF"))
        assertTrue(txt.contains("%%c16"))
        println("DXF: ${txt.lines().size} строк, LINE=${Regex("\nLINE\n").findAll(txt).count()}, CIRCLE=${Regex("\nCIRCLE\n").findAll(txt).count()}, TEXT=${Regex("\nTEXT\n").findAll(txt).count()}")
    }
}
