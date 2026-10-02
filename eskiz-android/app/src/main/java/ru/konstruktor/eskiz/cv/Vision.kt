package ru.konstruktor.eskiz.cv

import org.opencv.calib3d.Calib3d
import org.opencv.core.Core
import org.opencv.core.Mat
import org.opencv.core.MatOfPoint
import org.opencv.core.MatOfPoint2f
import org.opencv.core.Point
import org.opencv.core.Rect
import org.opencv.core.RotatedRect
import org.opencv.core.Scalar
import org.opencv.core.Size
import org.opencv.core.TermCriteria
import org.opencv.imgcodecs.Imgcodecs
import org.opencv.imgproc.Imgproc
import org.opencv.objdetect.ArucoDetector
import org.opencv.objdetect.Objdetect
import ru.konstruktor.eskiz.geom.Mat3
import ru.konstruktor.eskiz.geom.P
import ru.konstruktor.eskiz.geom.dist
import kotlin.math.PI
import kotlin.math.abs
import kotlin.math.cos
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sin
import kotlin.math.sqrt

/** Лист-мишень: 4 метки ArUco 4×4 по углам листа A4 (мм, ось Y вниз). */
object SheetSpec {
    const val W = 210.0
    const val H = 297.0
    const val MARKER = 40.0
    const val MARGIN = 15.0
    val origins = listOf(
        P(MARGIN, MARGIN),
        P(W - MARGIN - MARKER, MARGIN),
        P(W - MARGIN - MARKER, H - MARGIN - MARKER),
        P(MARGIN, H - MARGIN - MARKER),
    )

    fun corners(id: Int): List<P> {
        val o = origins[id]
        return listOf(o, P(o.x + MARKER, o.y), P(o.x + MARKER, o.y + MARKER), P(o.x, o.y + MARKER))
    }
}

object Vision {

    class AutoResult(
        /** Замкнутый внешний контур (вершины по порядку). */
        val outline: List<P>,
        /** Внутренние не круглые вырезы — тоже замкнутые контуры. */
        val cutouts: List<List<P>>,
        /** Отверстия: точки на краю каждой окружности. */
        val holes: List<List<P>>,
    )

    private fun readScaled(path: String, maxSide: Int, gray: Boolean): Pair<Mat, Double> {
        val img = Imgcodecs.imread(path, if (gray) Imgcodecs.IMREAD_GRAYSCALE else Imgcodecs.IMREAD_COLOR)
        val s = min(1.0, maxSide.toDouble() / max(img.cols(), img.rows()))
        if (s >= 1.0) return img to 1.0
        val out = Mat()
        Imgproc.resize(img, out, Size(img.cols() * s, img.rows() * s), 0.0, 0.0, Imgproc.INTER_AREA)
        img.release()
        return out to s
    }

    /** Углы на фото для привязки точек. */
    fun detectCorners(path: String): List<P> {
        val (gray, s) = readScaled(path, 1600, true)
        val corners = MatOfPoint()
        Imgproc.goodFeaturesToTrack(gray, corners, 800, 0.01, 6.0)
        if (corners.empty()) { gray.release(); return emptyList() }
        val c2f = MatOfPoint2f(*corners.toArray().map { Point(it.x, it.y) }.toTypedArray())
        Imgproc.cornerSubPix(gray, c2f, Size(4.0, 4.0), Size(-1.0, -1.0),
            TermCriteria(TermCriteria.EPS + TermCriteria.COUNT, 30, 0.01))
        val res = c2f.toArray().map { P(it.x / s, it.y / s) }
        gray.release(); corners.release(); c2f.release()
        return res
    }

    /**
     * Автоматический контур детали. [rect] — рамка вокруг детали в координатах фото
     * (или null — вся картинка), [tap] — точка на детали, чтобы выбрать нужную.
     */
    fun autoContour(path: String, rect: Pair<P, P>?, tap: P?, corners: List<P>, detail: Double = 0.004): AutoResult? {
        val (img, s) = readScaled(path, 800, false)
        val w = img.cols(); val h = img.rows()
        val tapSmall = tap?.let { Point(it.x * s, it.y * s) }
        val r = if (rect == null && tapSmall != null) {
            tapRegion(img, tapSmall)
        } else if (rect != null) {
            val x0 = (min(rect.first.x, rect.second.x) * s).toInt().coerceIn(0, w - 2)
            val y0 = (min(rect.first.y, rect.second.y) * s).toInt().coerceIn(0, h - 2)
            val x1 = (max(rect.first.x, rect.second.x) * s).toInt().coerceIn(x0 + 1, w - 1)
            val y1 = (max(rect.first.y, rect.second.y) * s).toInt().coerceIn(y0 + 1, h - 1)
            Rect(x0, y0, x1 - x0, y1 - y0)
        } else {
            val m = (min(w, h) * 0.02).toInt().coerceAtLeast(2)
            Rect(m, m, w - 2 * m, h - 2 * m)
        }
        if (r.width < 8 || r.height < 8) { img.release(); return null }

        val mask = Mat()
        val bgd = Mat(); val fgd = Mat()
        Imgproc.grabCut(img, mask, r, bgd, fgd, 4, Imgproc.GC_INIT_WITH_RECT)
        val fg = Mat(); val pr = Mat()
        Core.compare(mask, Scalar(Imgproc.GC_FGD.toDouble()), fg, Core.CMP_EQ)
        Core.compare(mask, Scalar(Imgproc.GC_PR_FGD.toDouble()), pr, Core.CMP_EQ)
        Core.bitwise_or(fg, pr, fg)
        val k = Imgproc.getStructuringElement(Imgproc.MORPH_ELLIPSE, Size(5.0, 5.0))
        Imgproc.morphologyEx(fg, fg, Imgproc.MORPH_CLOSE, k)
        Imgproc.morphologyEx(fg, fg, Imgproc.MORPH_OPEN, k)

        val contours = ArrayList<MatOfPoint>()
        val hier = Mat()
        Imgproc.findContours(fg, contours, hier, Imgproc.RETR_CCOMP, Imgproc.CHAIN_APPROX_NONE)
        listOf(mask, bgd, fgd, fg, pr, k).forEach { it.release() }
        if (contours.isEmpty()) { img.release(); hier.release(); return null }

        fun hierOf(i: Int) = hier.get(0, i) // [next, prev, firstChild, parent]
        val outers = contours.indices.filter { hierOf(it)[3] < 0 }
        val outerIdx = outers
            .filter { tapSmall == null || Imgproc.pointPolygonTest(MatOfPoint2f(*contours[it].toArray()), tapSmall, false) >= 0 }
            .maxByOrNull { Imgproc.contourArea(contours[it]) }
            ?: outers.maxByOrNull { Imgproc.contourArea(contours[it]) }!!
        val outerArea = Imgproc.contourArea(contours[outerIdx])
        if (outerArea < 0.002 * w * h) { img.release(); hier.release(); return null }

        val snapR = 3.0 / s
        val outline = simplify(contours[outerIdx], detail).map { snap(P(it.x / s, it.y / s), corners, snapR) }

        val cutouts = ArrayList<List<P>>()
        val holes = ArrayList<List<P>>()
        var child = hierOf(outerIdx)[2].toInt()
        while (child >= 0) {
            val c = contours[child]
            val area = Imgproc.contourArea(c)
            if (area > 40) {
                val c2f = MatOfPoint2f(*c.toArray())
                val per = Imgproc.arcLength(c2f, true)
                val circularity = 4 * PI * area / (per * per)
                if (circularity > 0.8 && c.rows() >= 5) {
                    holes += ellipsePoints(Imgproc.fitEllipse(c2f)).map { P(it.x / s, it.y / s) }
                } else {
                    cutouts += simplify(c, detail * 2).map { snap(P(it.x / s, it.y / s), corners, snapR) }
                }
                c2f.release()
            }
            child = hierOf(child)[0].toInt()
        }
        img.release(); hier.release()

        // Отверстия по краям в полном разрешении — точнее, чем по маске.
        val fine = findHoles(path, outline)
        val merged = ArrayList<List<P>>(fine)
        for (hc in holes) {
            val c = ru.konstruktor.eskiz.geom.fitCircle(hc) ?: continue
            if (merged.none { other -> sameCircle(c, other) }) merged += hc
        }
        // Субпиксельное уточнение края каждого отверстия по полному разрешению.
        val full = Imgcodecs.imread(path, Imgcodecs.IMREAD_GRAYSCALE)
        val refined = merged.map { refineHole(full, it) ?: it }
        full.release()
        return AutoResult(outline, cutouts, refined)
    }

    /**
     * Уточнение края отверстия: по 64 лучам из центра ищем, где яркость проходит середину
     * между «внутри» и «снаружи» (с субпиксельной интерполяцией), и заново вписываем эллипс.
     */
    private fun refineHole(gray: Mat, pts: List<P>): List<P>? {
        if (pts.size < 5) return null
        val e0 = Imgproc.fitEllipse(MatOfPoint2f(*pts.map { Point(it.x, it.y) }.toTypedArray()))
        val c = P(e0.center.x, e0.center.y)
        val rMax = max(e0.size.width, e0.size.height) / 2 * 1.45 + 3
        val x0 = (c.x - rMax).toInt().coerceAtLeast(0); val y0 = (c.y - rMax).toInt().coerceAtLeast(0)
        val x1 = (c.x + rMax).toInt().coerceAtMost(gray.cols() - 1); val y1 = (c.y + rMax).toInt().coerceAtMost(gray.rows() - 1)
        val rw = x1 - x0 + 1; val rh = y1 - y0 + 1
        if (rw < 8 || rh < 8) return null
        val buf = ByteArray(rw * rh)
        gray.submat(y0, y1 + 1, x0, x1 + 1).clone().also { it.get(0, 0, buf); it.release() }
        fun at(x: Double, y: Double): Double {
            val fx = x - x0; val fy = y - y0
            val ix = fx.toInt(); val iy = fy.toInt()
            if (ix < 0 || iy < 0 || ix >= rw - 1 || iy >= rh - 1) return Double.NaN
            val ax = fx - ix; val ay = fy - iy
            fun v(xx: Int, yy: Int) = (buf[yy * rw + xx].toInt() and 0xFF).toDouble()
            return v(ix, iy) * (1 - ax) * (1 - ay) + v(ix + 1, iy) * ax * (1 - ay) + v(ix, iy + 1) * (1 - ax) * ay + v(ix + 1, iy + 1) * ax * ay
        }
        val edge = ArrayList<Point>()
        for (k in 0 until 64) {
            val t = 2 * PI * k / 64
            val q = ellipsePoints(e0, 64)[k]
            val dir = (P(q.x, q.y) - c)
            val r = dir.len()
            if (r < 2) continue
            val u = dir / r
            val step = 0.25
            val n = ((0.8 * r) / step).toInt()
            val vals = DoubleArray(n + 1) { i -> val sr = 0.6 * r + i * step; at(c.x + u.x * sr, c.y + u.y * sr) }
            if (vals.any { it.isNaN() }) continue
            val q1 = (n * 0.18).toInt().coerceAtLeast(1)
            val iin = vals.take(q1).average(); val iout = vals.takeLast(q1).average()
            if (abs(iin - iout) < 15) continue
            val mid = (iin + iout) / 2
            var best = Double.NaN
            for (i in 0 until n) {
                val a = vals[i] - mid; val b = vals[i + 1] - mid
                if (a == 0.0 || a * b < 0) {
                    val sr = 0.6 * r + (i + if (a == 0.0) 0.0 else a / (a - b)) * step
                    if (best.isNaN() || abs(sr - r) < abs(best - r)) best = sr
                }
            }
            if (!best.isNaN()) edge += Point(c.x + u.x * best, c.y + u.y * best)
            if (t < 0) break
        }
        if (edge.size < 24) return null
        val e = Imgproc.fitEllipse(MatOfPoint2f(*edge.toTypedArray()))
        return ellipsePoints(e).map { P(it.x, it.y) }
    }

    /** Область детали вокруг точки касания: заливка похожим цветом, затем запас по краям. */
    internal fun tapRegion(img: Mat, tap: Point): Rect {
        val w = img.cols(); val h = img.rows()
        val blur = Mat()
        Imgproc.GaussianBlur(img, blur, Size(7.0, 7.0), 0.0)
        val mask = Mat.zeros(h + 2, w + 2, org.opencv.core.CvType.CV_8UC1)
        // Сравнение с цветом в точке касания (а не с соседом) — не «утекает» по плавным переходам.
        val flags = 4 or (255 shl 8) or Imgproc.FLOODFILL_MASK_ONLY or Imgproc.FLOODFILL_FIXED_RANGE
        val tol = Scalar(32.0, 32.0, 32.0)
        Imgproc.floodFill(blur, mask, tap, Scalar(0.0), Rect(), tol, tol, flags)
        // OpenCV ставит 1 по рамке маски — берём только залитое (255) внутри.
        val filled = Mat()
        Core.compare(mask.submat(1, h + 1, 1, w + 1), Scalar(255.0), filled, Core.CMP_EQ)
        val nz = Mat()
        Core.findNonZero(filled, nz)
        val bb = if (nz.empty()) Rect(tap.x.toInt(), tap.y.toInt(), 1, 1) else Imgproc.boundingRect(nz)
        blur.release(); mask.release(); filled.release(); nz.release()
        // Слишком маленькая область (блики, текстура) — берём окрестность касания.
        val minSide = min(w, h) * 0.15
        var x0 = bb.x.toDouble(); var y0 = bb.y.toDouble(); var x1 = x0 + bb.width; var y1 = y0 + bb.height
        if (x1 - x0 < minSide) { val c = (x0 + x1) / 2; x0 = c - minSide / 2; x1 = c + minSide / 2 }
        if (y1 - y0 < minSide) { val c = (y0 + y1) / 2; y0 = c - minSide / 2; y1 = c + minSide / 2 }
        val mx = (x1 - x0) * 0.2; val my = (y1 - y0) * 0.2
        val rx0 = (x0 - mx).toInt().coerceIn(1, w - 3); val ry0 = (y0 - my).toInt().coerceIn(1, h - 3)
        val rx1 = (x1 + mx).toInt().coerceIn(rx0 + 2, w - 2); val ry1 = (y1 + my).toInt().coerceIn(ry0 + 2, h - 2)
        return Rect(rx0, ry0, rx1 - rx0, ry1 - ry0)
    }

    private fun sameCircle(c: ru.konstruktor.eskiz.geom.Circle, pts: List<P>): Boolean {
        val o = ru.konstruktor.eskiz.geom.fitCircle(pts) ?: return false
        return dist(c.c, o.c) < 0.3 * max(c.r, o.r) && abs(c.r - o.r) < 0.25 * max(c.r, o.r)
    }

    private fun simplify(c: MatOfPoint, detail: Double): List<Point> {
        val c2f = MatOfPoint2f(*c.toArray())
        val eps = detail * Imgproc.arcLength(c2f, true)
        val approx = MatOfPoint2f()
        Imgproc.approxPolyDP(c2f, approx, eps, true)
        val res = approx.toArray().toList()
        c2f.release(); approx.release()
        return res
    }

    private fun snap(p: P, corners: List<P>, r: Double): P {
        val best = corners.minByOrNull { dist(it, p) } ?: return p
        return if (dist(best, p) <= r) best else p
    }

    private fun ellipsePoints(e: RotatedRect, n: Int = 16): List<Point> {
        val a = e.size.width / 2; val b = e.size.height / 2
        val th = e.angle * PI / 180
        return (0 until n).map {
            val t = 2 * PI * it / n
            val x = a * cos(t); val y = b * sin(t)
            Point(e.center.x + x * cos(th) - y * sin(th), e.center.y + x * sin(th) + y * cos(th))
        }
    }

    /** Поиск круглых отверстий внутри контура по границам (Canny + эллипсы). */
    private fun findHoles(path: String, outline: List<P>): List<List<P>> {
        if (outline.size < 3) return emptyList()
        val (gray, s) = readScaled(path, 2000, true)
        val minX = outline.minOf { it.x } * s; val maxX = outline.maxOf { it.x } * s
        val minY = outline.minOf { it.y } * s; val maxY = outline.maxOf { it.y } * s
        val x0 = minX.toInt().coerceIn(0, gray.cols() - 2); val y0 = minY.toInt().coerceIn(0, gray.rows() - 2)
        val x1 = maxX.toInt().coerceIn(x0 + 1, gray.cols() - 1); val y1 = maxY.toInt().coerceIn(y0 + 1, gray.rows() - 1)
        val roi = Mat(gray, Rect(x0, y0, x1 - x0, y1 - y0))
        val blur = Mat(); val edges = Mat()
        Imgproc.GaussianBlur(roi, blur, Size(5.0, 5.0), 0.0)
        Imgproc.Canny(blur, edges, 40.0, 120.0)
        val contours = ArrayList<MatOfPoint>()
        Imgproc.findContours(edges, contours, Mat(), Imgproc.RETR_LIST, Imgproc.CHAIN_APPROX_NONE)
        val outlineSmall = MatOfPoint2f(*outline.map { Point(it.x * s - x0, it.y * s - y0) }.toTypedArray())
        val minR = max(4.0, min(roi.cols(), roi.rows()) * 0.012)
        val maxR = min(roi.cols(), roi.rows()) * 0.45
        val found = ArrayList<Pair<RotatedRect, Double>>()
        for (c in contours) {
            if (c.rows() < 20) continue
            val c2f = MatOfPoint2f(*c.toArray())
            val e = Imgproc.fitEllipse(c2f)
            val a = e.size.width / 2; val b = e.size.height / 2
            val rMin = min(a, b); val rMax = max(a, b)
            if (rMin < minR || rMax > maxR || rMin / rMax < 0.5) { c2f.release(); continue }
            // Насколько точки ложатся на эллипс и насколько контур замкнут.
            val th = e.angle * PI / 180
            var err = 0.0
            val pts = c.toArray()
            for (p in pts) {
                val dx = p.x - e.center.x; val dy = p.y - e.center.y
                val u = dx * cos(th) + dy * sin(th); val v = -dx * sin(th) + dy * cos(th)
                err += abs(sqrt((u / a) * (u / a) + (v / b) * (v / b)) - 1)
            }
            err /= pts.size
            val perim = PI * (3 * (a + b) - sqrt((3 * a + b) * (a + 3 * b)))
            val coverage = Imgproc.arcLength(c2f, false) / perim
            c2f.release()
            if (err > 0.03 || coverage < 0.75) continue
            val inside = Imgproc.pointPolygonTest(outlineSmall, e.center, true)
            if (inside < rMin * 0.6) continue
            found += e to (a + b) / 2
        }
        // У края отверстия два контура (по обе стороны линии границы) — усредняем их.
        val groups = ArrayList<MutableList<RotatedRect>>()
        for ((e, rr) in found.sortedByDescending { it.second }) {
            val g = groups.firstOrNull { grp ->
                val o = grp[0]
                val or = (o.size.width + o.size.height) / 4
                val d = sqrt((o.center.x - e.center.x).let { it * it } + (o.center.y - e.center.y).let { it * it })
                d < 0.3 * or && abs(or - rr) < 0.25 * or
            }
            if (g != null) g += e else groups += mutableListOf(e)
        }
        listOf(roi, blur, edges, outlineSmall, gray).forEach { it.release() }
        return groups.map { grp ->
            val e = RotatedRect(
                Point(grp.sumOf { it.center.x } / grp.size, grp.sumOf { it.center.y } / grp.size),
                Size(grp.sumOf { it.size.width } / grp.size, grp.sumOf { it.size.height } / grp.size),
                grp[0].angle,
            )
            ellipsePoints(e).map { P((it.x + x0) / s, (it.y + y0) / s) }
        }
    }

    /** Поиск листа-мишени. Возвращает гомографию «пиксели → мм листа» и число найденных меток. */
    fun detectSheet(path: String): Pair<Mat3, Int>? {
        val gray = Imgcodecs.imread(path, Imgcodecs.IMREAD_GRAYSCALE)
        val detector = ArucoDetector(Objdetect.getPredefinedDictionary(Objdetect.DICT_4X4_50))
        val corners = ArrayList<Mat>()
        val ids = Mat()
        detector.detectMarkers(gray, corners, ids)
        gray.release()
        val img = ArrayList<Point>(); val world = ArrayList<Point>()
        var count = 0
        for (i in 0 until ids.rows()) {
            val id = ids.get(i, 0)[0].toInt()
            if (id !in 0..3) continue
            val c = corners[i]
            val wc = SheetSpec.corners(id)
            for (j in 0 until 4) {
                val v = c.get(0, j)
                img += Point(v[0], v[1]); world += Point(wc[j].x, wc[j].y)
            }
            count++
        }
        corners.forEach { it.release() }; ids.release()
        if (count == 0) return null
        val hm = Calib3d.findHomography(MatOfPoint2f(*img.toTypedArray()), MatOfPoint2f(*world.toTypedArray()), 0)
        if (hm.empty()) return null
        val m = DoubleArray(9) { hm.get(it / 3, it % 3)[0] }
        hm.release()
        return Mat3(m) to count
    }

    /** Изображение метки ArUco (8-бит, белая рамка в 1 клетку). */
    fun markerImage(id: Int, px: Int): Mat {
        val m = Mat()
        Objdetect.generateImageMarker(Objdetect.getPredefinedDictionary(Objdetect.DICT_4X4_50), id, px, m, 1)
        return m
    }
}
