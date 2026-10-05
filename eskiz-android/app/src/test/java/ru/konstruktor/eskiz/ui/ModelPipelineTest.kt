package ru.konstruktor.eskiz.ui

import android.app.Application
import android.graphics.Bitmap
import android.os.Looper
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.RuntimeEnvironment
import org.robolectric.Shadows.shadowOf
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode
import ru.konstruktor.eskiz.data.ModelStore
import ru.konstruktor.eskiz.data.Project
import ru.konstruktor.eskiz.data.ProjectStore
import ru.konstruktor.eskiz.data.SCircle
import ru.konstruktor.eskiz.data.SDim
import ru.konstruktor.eskiz.data.SLine
import ru.konstruktor.eskiz.data.SPoint
import ru.konstruktor.eskiz.geom.P
import ru.konstruktor.eskiz.geom3d.MultiView
import java.io.File
import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.sin

/** Полная цепочка: эскизы видов (точки на «фото» + размеры) → 3D-модель. */
@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(sdk = [34])
class ModelPipelineTest {
    private val app get() = RuntimeEnvironment.getApplication() as Application

    /** Эскиз вида: контур (мм, ось вверх) и отверстия; на «фото» 10 пикселей на мм. */
    private fun sketch(store: ProjectStore, id: String, outline: List<P>, holes: List<Pair<P, Double>>): String {
        fun img(p: P) = P(100 + p.x * 10, 1000 - p.y * 10)
        val pts = outline.mapIndexed { i, p -> val q = img(p); SPoint(i + 1, q.x, q.y) }
        val lines = pts.indices.map { SLine(100 + it, it + 1, (it + 1) % pts.size + 1) }
        // Известные размеры: две стороны и диагональ.
        fun d(a: Int, b: Int) = ru.konstruktor.eskiz.geom.dist(outline[a - 1], outline[b - 1])
        val dims = listOf(SDim(200, 1, 2, d(1, 2)), SDim(201, 2, 3, d(2, 3)), SDim(202, 1, 3, d(1, 3)))
        val circles = holes.mapIndexed { i, (c, r) -> SCircle(300 + i, (0 until 16).map { k -> img(P(c.x + r * cos(k * PI / 8), c.y + r * sin(k * PI / 8))) }) }
        store.dir(id).mkdirs()
        val bmp = Bitmap.createBitmap(200, 150, Bitmap.Config.ARGB_8888)
        store.photo(id).outputStream().use { bmp.compress(Bitmap.CompressFormat.JPEG, 80, it) }
        store.thumb(id).outputStream().use { bmp.compress(Bitmap.CompressFormat.JPEG, 80, it) }
        store.save(Project(id, id, 0, 0, 2000, 1200, pts, lines, dims, circles, nextId = 400))
        return id
    }

    @Test
    fun bracketFromSketches() {
        val ps = ProjectStore(app)
        val front = sketch(ps, "front", listOf(P(0.0, 0.0), P(100.0, 0.0), P(100.0, 10.0), P(10.0, 10.0), P(10.0, 60.0), P(0.0, 60.0)), emptyList())
        val top = sketch(ps, "top", listOf(P(0.0, 0.0), P(100.0, 0.0), P(100.0, 40.0), P(0.0, 40.0)), listOf(P(60.0, 20.0) to 6.0))
        val left = sketch(ps, "left", listOf(P(0.0, 0.0), P(40.0, 0.0), P(40.0, 60.0), P(0.0, 60.0)), listOf(P(20.0, 40.0) to 5.0))

        val ms = ModelStore(app)
        val id = ms.create("Кронштейн").id
        val vm = ModelViewModel(app, id)
        vm.setView(MultiView.Role.FRONT, front)
        vm.setView(MultiView.Role.TOP, top)
        vm.setView(MultiView.Role.LEFT, left)
        waitBuilt(vm)
        assertTrue("ошибки: ${vm.viewErrors} ${vm.error}", vm.viewErrors.isEmpty() && vm.error == null)
        val r = vm.result
        assertNotNull(r)
        val expected = 1500.0 * 40 - PI * 36 * 10 - PI * 25 * 10
        println("Из эскизов: объём ${r!!.solid.volume} (ожид. $expected), размер ${r.size}, ${r.warnings}")
        assertEquals(expected, r.solid.volume, expected * 0.01)
        assertEquals(0, r.solid.openEdges())

        // Модель сохраняется вместе с видами (отложенно — ждём запись).
        Thread.sleep(600); shadowOf(Looper.getMainLooper()).idle(); Thread.sleep(200)
        assertEquals(3, ms.load(id).views.size)

        val out = File("build/render-test").apply { mkdirs() }
        val bmp = vm.render(640, 480, Math.toRadians(-35.0), Math.toRadians(25.0))!!
        File(out, "model_preview.png").outputStream().use { bmp.compress(Bitmap.CompressFormat.PNG, 100, it) }

        var file: File? = null
        vm.export(Model3DExport.STEP) { file = it }
        repeat(200) { if (file == null) { shadowOf(Looper.getMainLooper()).idle(); Thread.sleep(20) } }
        assertNotNull(file)
        file!!.copyTo(File(out, "model_bracket.step"), overwrite = true)

        // Один вид без толщины — понятная ошибка; с толщиной — модель.
        vm.setView(MultiView.Role.TOP, null); vm.setView(MultiView.Role.LEFT, null)
        waitBuilt(vm)
        assertTrue(vm.error?.contains("толщину") == true)
        vm.setThickness(5.0)
        waitBuilt(vm)
        assertEquals(1500.0 * 5, vm.result!!.solid.volume, 1500.0 * 5 * 0.01)
    }

    private fun waitBuilt(vm: ModelViewModel) {
        val looper = shadowOf(Looper.getMainLooper())
        var n = 0
        do { looper.idle(); Thread.sleep(20); n++ } while ((vm.building) && n < 1000)
        looper.idle()
    }
}
