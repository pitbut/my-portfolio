package ru.konstruktor.eskiz.shots

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.compose.ui.test.captureToImage
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onRoot
import androidx.compose.ui.test.performClick
import org.junit.Assume.assumeTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.RuntimeEnvironment
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode
import ru.konstruktor.eskiz.EskizTheme
import ru.konstruktor.eskiz.data.ModelStore
import ru.konstruktor.eskiz.data.Project
import ru.konstruktor.eskiz.data.ProjectStore
import ru.konstruktor.eskiz.data.SCircle
import ru.konstruktor.eskiz.data.SDim
import ru.konstruktor.eskiz.data.SLine
import ru.konstruktor.eskiz.data.SPoint
import ru.konstruktor.eskiz.data.Stamp
import ru.konstruktor.eskiz.data.ViewRef
import ru.konstruktor.eskiz.geom.P
import ru.konstruktor.eskiz.geom.dist
import ru.konstruktor.eskiz.ui.EditorScreen
import ru.konstruktor.eskiz.ui.ModelScreen
import ru.konstruktor.eskiz.ui.ProjectListScreen
import java.io.File

/**
 * Скриншоты настоящих экранов для RuStore (1080×1920). Запуск:
 * ESKIZ_SHOTS=<папка с фото> ./gradlew testDebugUnitTest --tests '*StoreScreenshots*'
 */
@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(sdk = [34], qualifiers = "w360dp-h640dp-xxhdpi")
class StoreScreenshots {
    @get:Rule val rule = createAndroidComposeRule<androidx.activity.ComponentActivity>()

    private val dir = System.getenv("ESKIZ_SHOTS")?.let(::File)
    private val out = File("build/store-shots").apply { mkdirs() }

    private fun parse(f: File): Pair<List<P>, Pair<List<P>, List<List<P>>>> {
        fun pts(s: String) = s.split(";").map { val (x, y) = it.split(","); P(x.toDouble(), y.toDouble()) }
        val lines = f.readLines()
        val outline = pts(lines.first { it.startsWith("outline=") }.removePrefix("outline="))
        val world = pts(lines.first { it.startsWith("world=") }.removePrefix("world="))
        val holes = lines.filter { it.startsWith("hole=") }.map { pts(it.removePrefix("hole=")) }
        return outline to (world to holes)
    }

    /** Эскиз из «фото»: контур, отверстия и размеры (известные — [known] пары вершин, 1-based). */
    private fun sketch(store: ProjectStore, name: String, title: String, known: List<Pair<Int, Int>>, computed: List<Pair<Int, Int>>, knownHole: Int?): String {
        val (outline, wh) = parse(File(dir, "$name.txt"))
        val (world, holes) = wh
        val id = "shot-$name"
        store.dir(id).mkdirs()
        File(dir, "$name.jpg").copyTo(store.photo(id), overwrite = true)
        val bmp = BitmapFactory.decodeFile(store.photo(id).absolutePath)
        Bitmap.createScaledBitmap(bmp, 300, 400, true).let { th -> store.thumb(id).outputStream().use { th.compress(Bitmap.CompressFormat.JPEG, 85, it) } }
        val pts = outline.mapIndexed { i, p -> SPoint(i + 1, p.x, p.y) }
        val lines = pts.indices.map { SLine(100 + it, it + 1, (it + 1) % pts.size + 1) }
        var nid = 200
        val dims = known.map { (a, b) -> SDim(nid++, a, b, Math.round(dist(world[a - 1], world[b - 1]) * 10) / 10.0) } +
            computed.map { (a, b) -> SDim(nid++, a, b, null) }
        val circles = holes.mapIndexed { i, h -> SCircle(300 + i, h, if (i == knownHole) 16.0 else null) }
        store.save(Project(id, title, 0, System.currentTimeMillis() - (dims.size * 3600_000L), 1800, 2400, pts, lines, dims, circles,
            nextId = 400, stamp = Stamp(title, "Иванов", "Ст3")))
        return id
    }

    private fun settle(ms: Long = 4000) {
        val end = System.currentTimeMillis() + ms
        while (System.currentTimeMillis() < end) { rule.waitForIdle(); Thread.sleep(100) }
    }

    private fun shot(name: String) {
        // Рисуем окно приложения на холст (captureToImage под Robolectric ждёт кадр бесконечно).
        val v = rule.activity.window.decorView
        val bmp = Bitmap.createBitmap(v.width, v.height, Bitmap.Config.ARGB_8888)
        rule.runOnUiThread { v.draw(android.graphics.Canvas(bmp)) }
        File(out, "shot_${name.substring(0, 1)}.png").outputStream().use { bmp.compress(Bitmap.CompressFormat.PNG, 100, it) }
        println("$name: ${bmp.width}×${bmp.height}")
    }

    @Test
    fun storeScreens() {
        assumeTrue("нет ESKIZ_SHOTS", dir != null && dir.exists())
        val app = RuntimeEnvironment.getApplication()
        val ps = ProjectStore(app)
        // Виды кронштейна: все стороны и обе диагонали — так рекомендует приложение для точности.
        val rect = listOf(1 to 2, 2 to 3, 3 to 4, 4 to 1, 1 to 3, 2 to 4)
        val left = sketch(ps, "left", "Вид слева", rect, emptyList(), null)
        val top = sketch(ps, "top", "Вид сверху", rect, emptyList(), null)
        val front = sketch(ps, "front", "Вид спереди", listOf(1 to 2, 2 to 3, 3 to 4, 4 to 5, 5 to 6, 6 to 1, 1 to 5, 2 to 6), emptyList(), null)
        val plate = sketch(ps, "plate", "Пластина опорная", listOf(1 to 2, 2 to 3, 5 to 6, 6 to 1, 1 to 3), listOf(3 to 4, 4 to 5), 0)
        val ms = ModelStore(app)
        val model = ms.create("Кронштейн").copy(views = listOf(ViewRef(front, "FRONT"), ViewRef(top, "TOP"), ViewRef(left, "LEFT")))
        ms.save(model)

        var screen by mutableStateOf(0)
        rule.setContent {
            EskizTheme {
                when (screen) {
                    0 -> EditorScreen(plate, onBack = {})
                    1 -> ModelScreen(model.id, onBack = {}, onOpenSketch = {})
                    else -> ProjectListScreen(tab = 0, onTab = {}, onOpen = {}, onOpenModel = {})
                }
            }
        }
        settle(6000)
        shot("1_фото_с_размерами")
        rule.onNodeWithContentDescription("Чертёж").performClick()
        settle(3000)
        shot("2_чертёж")
        screen = 1
        settle(8000)
        shot("3_3d_модель")
        screen = 2
        settle(4000)
        shot("4_эскизы")
    }
}
