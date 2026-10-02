package ru.konstruktor.eskiz.export

import android.content.ClipData
import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Matrix
import android.graphics.Paint
import android.graphics.Typeface
import android.graphics.pdf.PdfDocument
import android.net.Uri
import androidx.core.content.FileProvider
import ru.konstruktor.eskiz.cv.SheetSpec
import ru.konstruktor.eskiz.cv.Vision
import ru.konstruktor.eskiz.data.Project
import ru.konstruktor.eskiz.geom.Calibration
import ru.konstruktor.eskiz.geom.DimLayout
import ru.konstruktor.eskiz.geom.P
import ru.konstruktor.eskiz.render.CanvasPen
import ru.konstruktor.eskiz.render.DrawingModel
import ru.konstruktor.eskiz.render.PageSpec
import ru.konstruktor.eskiz.render.Renderer
import ru.konstruktor.eskiz.render.fmtMm
import java.io.File
import java.util.Locale
import kotlin.math.max

object Exporters {

    private fun shareDir(ctx: Context) = File(ctx.cacheDir, "share").apply { mkdirs() }

    private fun safeName(p: Project) = p.name.replace(Regex("[^\\p{L}\\p{N}_ -]"), "_").trim().ifBlank { "eskiz" }

    /** Чертёж на листе A4 в PNG. */
    fun drawingPng(ctx: Context, project: Project, cal: Calibration): File {
        val model = DrawingModel(project, cal)
        val page = PageSpec.choose(model.bounds)
        val k = 8f // 8 пикселей на мм ≈ 200 dpi
        val bmp = Bitmap.createBitmap((page.w * k).toInt(), (page.h * k).toInt(), Bitmap.Config.ARGB_8888)
        Renderer.drawPage(CanvasPen(Canvas(bmp)), model, page, k, 0f, 0f)
        val f = File(shareDir(ctx), "${safeName(project)}_чертёж.png")
        f.outputStream().use { bmp.compress(Bitmap.CompressFormat.PNG, 100, it) }
        bmp.recycle()
        return f
    }

    /** Фото с нанесёнными размерами в PNG/JPEG. */
    fun photoJpg(ctx: Context, project: Project, cal: Calibration, photo: File): File {
        val src = BitmapFactory.decodeFile(photo.absolutePath)
        val s = minOf(1f, 2400f / max(src.width, src.height))
        // Рисуем на заведомо изменяемой копии нужного размера.
        val bmp = Bitmap.createBitmap((src.width * s).toInt(), (src.height * s).toInt(), Bitmap.Config.ARGB_8888)
        val c = Canvas(bmp)
        c.drawBitmap(src, Matrix().apply { postScale(s, s) }, Paint(Paint.FILTER_BITMAP_FLAG))
        src.recycle()
        val scale = bmp.width.toDouble() / project.imageW
        val dp = max(bmp.width, bmp.height) / 900f
        Renderer.drawPhotoOverlay(CanvasPen(c), project, cal, { p -> p * scale }, dp, Renderer.PhotoOverlay())
        val f = File(shareDir(ctx), "${safeName(project)}_фото.jpg")
        f.outputStream().use { bmp.compress(Bitmap.CompressFormat.JPEG, 92, it) }
        bmp.recycle()
        return f
    }

    fun drawingPdf(ctx: Context, project: Project, cal: Calibration): File {
        val model = DrawingModel(project, cal)
        val page = PageSpec.choose(model.bounds)
        val k = (72 / 25.4).toFloat()
        val doc = PdfDocument()
        val pg = doc.startPage(PdfDocument.PageInfo.Builder((page.w * k).toInt(), (page.h * k).toInt(), 1).create())
        Renderer.drawPage(CanvasPen(pg.canvas), model, page, k, 0f, 0f)
        doc.finishPage(pg)
        val f = File(shareDir(ctx), "${safeName(project)}_чертёж.pdf")
        f.outputStream().use { doc.writeTo(it) }
        doc.close()
        return f
    }

    /** DXF (R12, мм, 1:1): слои CONTOUR, AXIS, DIM. Понимают AutoCAD, КОМПАС, nanoCAD, FreeCAD. */
    fun drawingDxf(ctx: Context, project: Project, cal: Calibration): File {
        val model = DrawingModel(project, cal)
        val page = PageSpec.choose(model.bounds)
        val m = page.scale
        val out = StringBuilder()
        fun g(code: Int, v: Any) {
            out.append(code).append('\n')
            out.append(if (v is Double) String.format(Locale.US, "%.4f", v) else v.toString()).append('\n')
        }
        // В DXF ось Y вверх.
        fun xy(p: P, cx: Int = 10) { g(cx, p.x); g(cx + 10, -p.y) }

        g(0, "SECTION"); g(2, "HEADER"); g(9, "\$ACADVER"); g(1, "AC1009"); g(0, "ENDSEC")
        g(0, "SECTION"); g(2, "TABLES")
        g(0, "TABLE"); g(2, "LTYPE"); g(70, 1)
        g(0, "LTYPE"); g(2, "CONTINUOUS"); g(70, 0); g(3, "Solid line"); g(72, 65); g(73, 0); g(40, 0.0)
        g(0, "ENDTAB")
        g(0, "TABLE"); g(2, "LAYER"); g(70, 3)
        for ((name, color) in listOf("CONTOUR" to 7, "AXIS" to 1, "DIM" to 3)) {
            g(0, "LAYER"); g(2, name); g(70, 0); g(62, color); g(6, "CONTINUOUS")
        }
        g(0, "ENDTAB")
        g(0, "ENDSEC")
        g(0, "SECTION"); g(2, "ENTITIES")

        fun lineE(a: P, b: P, layer: String) { g(0, "LINE"); g(8, layer); xy(a); xy(b, 11) }
        fun textE(s: String, at: P, h: Double, angDeg: Double) {
            g(0, "TEXT"); g(8, "DIM"); xy(at); g(40, h); g(1, s); g(50, angDeg); g(72, 1); xy(at, 11); g(73, 2)
        }
        fun solidE(a: P, b: P, c: P) { g(0, "SOLID"); g(8, "DIM"); xy(a); xy(b, 11); xy(c, 12); xy(c, 13) }

        for ((a, b) in model.lines) lineE(a, b, "CONTOUR")
        for (ci in model.circles) {
            g(0, "CIRCLE"); g(8, "CONTOUR"); xy(ci.circle.c); g(40, ci.circle.r)
            val e = ci.circle.r + 2 / m
            lineE(ci.circle.c - P(e, 0.0), ci.circle.c + P(e, 0.0), "AXIS")
            lineE(ci.circle.c - P(0.0, e), ci.circle.c + P(0.0, e), "AXIS")
        }

        // Дуги: в DXF угол против часовой при оси Y вверх, а у нас Y вниз — углы меняют знак.
        for (ai in model.arcs) {
            val a = ai.arc
            var s0 = -Math.toDegrees(a.start); var s1 = -Math.toDegrees(a.end)
            if (s1 < s0) { val t = s0; s0 = s1; s1 = t } // DXF рисует от начала к концу против часовой
            g(0, "ARC"); g(8, "CONTOUR"); xy(a.c); g(40, a.r); g(50, (s0 % 360 + 360) % 360); g(51, (s1 % 360 + 360) % 360)
        }

        // Размеры — линиями, стрелками и текстом (так их читает любая программа).
        val th = 3.5 / m
        val arrowL = 3.0 / m
        val params = DimLayout.Params(th, 10 / m, 7 / m, arrowL) { it.length * th * 0.75 }
        val layout = DimLayout.layout(
            model.lines + model.arcs.flatMap { it.arc.sample(12).zipWithNext() }, model.circles.map { it.circle },
            model.dims.map { DimLayout.LinearIn(it.id, it.a, it.b, it.value?.let(::fmtMm) ?: "?") },
            model.circles.map { DimLayout.DiameterIn(it.id, it.circle.c, it.circle.r, "%%c" + (it.value?.let(::fmtMm) ?: "?")) } +
                model.arcs.map { DimLayout.DiameterIn(it.id, it.arc.c, it.arc.r, "R" + (it.value?.let(::fmtMm) ?: "?"), Renderer.radiusAngles(it.arc)) },
            params,
        )
        fun arrow(tip: P, dir: P) {
            val d = dir.norm(); val n = d.perp(); val base = tip + d * arrowL
            solidE(tip, base + n * (arrowL / 6), base - n * (arrowL / 6))
        }
        for (d in layout.linear) {
            val u = (d.db - d.da).norm()
            for ((p, q) in listOf(d.a to d.da, d.b to d.db)) {
                val dir = q - p
                if (dir.len() > 1e-9) lineE(p, q + dir.norm() * (2 / m), "DIM")
            }
            val len = ru.konstruktor.eskiz.geom.dist(d.da, d.db)
            val tw = d.text.length * th * 0.75
            val tProj = (d.textCenter - d.da).dot(u) + tw / 2
            lineE(if (d.arrowsOutside) d.da - u * (arrowL * 2) else d.da,
                if (tProj > len) d.da + u * tProj else if (d.arrowsOutside) d.db + u * (arrowL * 2) else d.db, "DIM")
            if (d.arrowsOutside) { arrow(d.da, -u); arrow(d.db, u) } else { arrow(d.da, u); arrow(d.db, -u) }
            // Угол в DXF отсчитывается против часовой при оси Y вверх.
            textE(d.text, d.textCenter, th, -Math.toDegrees(d.textAngle))
        }
        for (d in layout.diameters) {
            lineE(d.start, d.elbow, "DIM"); lineE(d.elbow, d.shelfEnd, "DIM")
            arrow(d.start, d.elbow - d.start)
            textE(d.text, d.textCenter, th, 0.0)
        }
        g(0, "ENDSEC"); g(0, "EOF")

        val f = File(shareDir(ctx), "${safeName(project)}.dxf")
        f.writeText(out.toString(), Charsets.US_ASCII)
        return f
    }

    /** Лист-мишень A4 для печати в масштабе 100%. */
    fun markerSheetPdf(ctx: Context): File {
        val k = (72 / 25.4).toFloat()
        val doc = PdfDocument()
        val pg = doc.startPage(PdfDocument.PageInfo.Builder((SheetSpec.W * k).toInt(), (SheetSpec.H * k).toInt(), 1).create())
        val c = pg.canvas
        c.drawColor(Color.WHITE)
        val paint = Paint(Paint.ANTI_ALIAS_FLAG).apply { isFilterBitmap = false }
        for (id in 0..3) {
            val bmp = markerBitmap(id, 600)
            val o = SheetSpec.origins[id]
            val mtx = Matrix().apply {
                val s = (SheetSpec.MARKER * k / bmp.width).toFloat()
                postScale(s, s); postTranslate((o.x * k).toFloat(), (o.y * k).toFloat())
            }
            c.drawBitmap(bmp, mtx, paint)
            bmp.recycle()
        }
        val tp = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.BLACK; textAlign = Paint.Align.CENTER; typeface = Typeface.DEFAULT_BOLD; textSize = 5f * k
        }
        val cx = (SheetSpec.W / 2 * k).toFloat()
        c.drawText("Лист-мишень «Эскиз»", cx, 80f * k, tp)
        tp.typeface = Typeface.DEFAULT; tp.textSize = 3.5f * k
        val lines = listOf(
            "Печатайте в масштабе 100% (без «подогнать под страницу»).",
            "Положите деталь в центр листа так, чтобы",
            "видно было хотя бы 2 метки по углам.",
            "Проверьте линейкой отрезок ниже — должно быть ровно 100 мм.",
        )
        lines.forEachIndexed { i, s -> c.drawText(s, cx, (92 + i * 6) * k, tp) }
        val lp = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.BLACK; strokeWidth = 0.4f * k }
        val y = 125f * k
        val x0 = (SheetSpec.W / 2 - 50) * k; val x1 = (SheetSpec.W / 2 + 50) * k
        c.drawLine(x0.toFloat(), y, x1.toFloat(), y, lp)
        for (i in 0..10) {
            val x = (x0 + i * 10 * k).toFloat()
            c.drawLine(x, y - (if (i % 5 == 0) 3f else 1.5f) * k, x, y, lp)
        }
        c.drawText("100 мм", cx, y + 6f * k, tp)
        doc.finishPage(pg)
        val f = File(shareDir(ctx), "Лист-мишень_A4.pdf")
        f.outputStream().use { doc.writeTo(it) }
        doc.close()
        return f
    }

    private fun markerBitmap(id: Int, px: Int): Bitmap {
        val m = Vision.markerImage(id, px)
        val rgba = org.opencv.core.Mat()
        org.opencv.imgproc.Imgproc.cvtColor(m, rgba, org.opencv.imgproc.Imgproc.COLOR_GRAY2RGBA)
        val bmp = Bitmap.createBitmap(px, px, Bitmap.Config.ARGB_8888)
        org.opencv.android.Utils.matToBitmap(rgba, bmp)
        m.release(); rgba.release()
        return bmp
    }

    fun share(ctx: Context, files: List<File>, title: String) {
        val auth = ctx.packageName + ".files"
        val uris: List<Uri> = files.map { FileProvider.getUriForFile(ctx, auth, it) }
        val intent = if (uris.size == 1) {
            Intent(Intent.ACTION_SEND).apply {
                type = mime(files[0])
                putExtra(Intent.EXTRA_STREAM, uris[0])
            }
        } else {
            Intent(Intent.ACTION_SEND_MULTIPLE).apply {
                type = "*/*"
                putParcelableArrayListExtra(Intent.EXTRA_STREAM, ArrayList(uris))
            }
        }
        intent.clipData = ClipData.newRawUri(null, uris[0]).apply { uris.drop(1).forEach { addItem(ClipData.Item(it)) } }
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        ctx.startActivity(Intent.createChooser(intent, title).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
    }

    private fun mime(f: File) = when (f.extension.lowercase()) {
        "png" -> "image/png"
        "jpg", "jpeg" -> "image/jpeg"
        "pdf" -> "application/pdf"
        "dxf" -> "application/dxf"
        else -> "application/octet-stream"
    }
}
