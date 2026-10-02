package ru.konstruktor.eskiz.ui

import android.app.Application
import android.graphics.Bitmap
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.RuntimeEnvironment
import org.robolectric.annotation.Config
import ru.konstruktor.eskiz.data.Project
import ru.konstruktor.eskiz.data.ProjectStore
import ru.konstruktor.eskiz.data.SLine
import ru.konstruktor.eskiz.data.SPoint
import ru.konstruktor.eskiz.geom.P

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [34])
class ContourEditTest {
    private val tol = 10.0

    /** Квадрат 1-2-3-4 со сторонами 100. */
    private fun vm(): EditorViewModel {
        val app = RuntimeEnvironment.getApplication() as Application
        val store = ProjectStore(app)
        val id = "test"
        store.dir(id).mkdirs()
        store.photo(id).outputStream().use { Bitmap.createBitmap(400, 400, Bitmap.Config.ARGB_8888).compress(Bitmap.CompressFormat.JPEG, 80, it) }
        val pts = listOf(SPoint(1, 100.0, 100.0), SPoint(2, 200.0, 100.0), SPoint(3, 200.0, 200.0), SPoint(4, 100.0, 200.0))
        val lines = listOf(SLine(5, 1, 2), SLine(6, 2, 3), SLine(7, 3, 4), SLine(8, 4, 1))
        store.save(Project(id, "t", 0, 0, 400, 400, pts, lines, nextId = 9))
        return EditorViewModel(app, id)
    }

    private fun EditorViewModel.edges() = project.lines.map { setOf(it.a, it.b) }.toSet()

    @Test
    fun insertPointIntoLineAndDeleteMergesNeighbours() {
        val vm = vm()
        vm.tool = Tool.POINT
        vm.place(P(150.0, 102.0), tol) // по верхней стороне
        assertEquals(5, vm.project.points.size)
        val n = vm.project.points.last().id
        assertEquals(P(150.0, 100.0), vm.project.point(n)!!.p) // точно на линии
        assertTrue(setOf(1, n) in vm.edges() && setOf(n, 2) in vm.edges())
        assertTrue(setOf(1, 2) !in vm.edges())

        // Удаляем вершину 2 — соединяются соседи n и 3.
        vm.selection = Selection.Point(2)
        vm.deleteSelection()
        assertEquals(setOf(setOf(1, n), setOf(n, 3), setOf(3, 4), setOf(4, 1)), vm.edges())
    }

    @Test
    fun lineBecomesArcAndArcDeletionRestoresLine() {
        val vm = vm()
        vm.tool = Tool.ARC
        vm.place(P(150.0, 101.0), tol)        // касание линии 1–2
        vm.place(P(150.0, 70.0), tol)         // точка, через которую пройдёт дуга
        assertEquals(1, vm.project.arcs.size)
        val arc = vm.project.arcs[0]
        assertEquals(setOf(1, 2), setOf(arc.a, arc.b))
        assertTrue(setOf(1, 2) !in vm.edges())
        assertNotNull(vm.dialog?.arcId)
        vm.saveDim(vm.dialog!!, 60.0)
        assertEquals(60.0, vm.project.arcs[0].known!!, 0.0)

        // Удаление середины дуги — снова прямая 1–2.
        vm.selection = Selection.Point(arc.m)
        vm.deleteSelection()
        assertTrue(vm.project.arcs.isEmpty())
        assertTrue(setOf(1, 2) in vm.edges())

        // Дуга по трём точкам, затем удаление самой дуги.
        vm.place(P(200.0, 100.0), tol); vm.place(P(230.0, 150.0), tol); vm.place(P(200.0, 200.0), tol)
        assertEquals(1, vm.project.arcs.size)
        assertTrue(setOf(2, 3) !in vm.edges())
        vm.dialog = null
        vm.selection = Selection.Arc(vm.project.arcs[0].id)
        vm.deleteSelection()
        assertTrue(vm.project.arcs.isEmpty() && setOf(2, 3) in vm.edges())
        assertEquals(4, vm.project.points.size) // точки середины дуг удалены, вершины целы
    }
}
