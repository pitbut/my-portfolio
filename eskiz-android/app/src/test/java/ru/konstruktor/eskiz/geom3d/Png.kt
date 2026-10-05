package ru.konstruktor.eskiz.geom3d

import java.io.ByteArrayOutputStream
import java.io.DataOutputStream
import java.io.File
import java.util.zip.CRC32
import java.util.zip.DeflaterOutputStream

/** Минимальная запись PNG (RGB) — в unit-тестах Android нет java.awt/ImageIO. */
object Png {
    fun write(file: File, px: IntArray, w: Int, h: Int) {
        val raw = ByteArrayOutputStream()
        DeflaterOutputStream(raw).use { z ->
            for (y in 0 until h) {
                z.write(0)
                for (x in 0 until w) { val c = px[y * w + x]; z.write(c shr 16 and 0xFF); z.write(c shr 8 and 0xFF); z.write(c and 0xFF) }
            }
        }
        val out = DataOutputStream(file.outputStream())
        out.write(byteArrayOf(0x89.toByte(), 'P'.code.toByte(), 'N'.code.toByte(), 'G'.code.toByte(), 13, 10, 26, 10))
        fun chunk(type: String, data: ByteArray) {
            out.writeInt(data.size)
            val td = type.toByteArray() + data
            out.write(td)
            out.writeInt(CRC32().apply { update(td) }.value.toInt())
        }
        val ihdr = ByteArrayOutputStream().also { DataOutputStream(it).apply { writeInt(w); writeInt(h); write(byteArrayOf(8, 2, 0, 0, 0)) } }
        chunk("IHDR", ihdr.toByteArray())
        chunk("IDAT", raw.toByteArray())
        chunk("IEND", ByteArray(0))
        out.close()
    }
}
