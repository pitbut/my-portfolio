package com.robutpit.pitbrowser.apps

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder
import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.io.File
import java.util.zip.ZipEntry
import java.util.zip.ZipOutputStream

class AppPlatformTest {
    @get:Rule val tmp = TemporaryFolder()

    private fun zip(vararg files: Pair<String, String>): ByteArray {
        val out = ByteArrayOutputStream()
        ZipOutputStream(out).use { z ->
            files.forEach { (name, body) -> z.putNextEntry(ZipEntry(name)); z.write(body.toByteArray()); z.closeEntry() }
        }
        return out.toByteArray()
    }

    private fun manifest(id: String = "my-game", version: String = "1.0.0", extra: String = "") =
        """{"id":"$id","name":"Игра","version":"$version","permissions":["sensors","scores"]$extra}"""

    // ------------------------------------------------------------ манифест

    @Test fun parsesManifest() {
        val m = AppManifest.parse("""{"id":"tilt","name":"Монетки","orientation":"portrait","permissions":["sensors","camera"],"scores":{"order":"asc","unit":"сек"}}""")
        assertEquals("index.html", m.entry)
        assertEquals("https://tilt.pitapp.robutpit.com", m.origin)
        assertTrue(m.has("camera"))
        assertEquals("asc", m.scoreOrder)
    }

    @Test fun rejectsBadManifest() {
        listOf(
            """{"id":"Bad_ID","name":"x"}""",
            """{"id":"ok","name":""}""",
            """{"id":"ok","name":"x","entry":"../evil.html"}""",
            """{"id":"ok","name":"x","permissions":["root"]}""",
            """{"id":"ok","name":"x","orientation":"diagonal"}""",
            "not json",
        ).forEach { assertThrows(it, InvalidPackageException::class.java) { AppManifest.parse(it) } }
    }

    // ------------------------------------------------------------ пакеты

    @Test fun installsAndServesFiles() {
        val p = AppPackages(tmp.newFolder("apps"))
        val m = p.install(ByteArrayInputStream(zip("manifest.json" to manifest(), "index.html" to "<h1>hi</h1>", "img/a.png" to "png")))
        assertEquals("my-game", m.id)
        assertEquals(listOf("my-game"), p.list().map { it.id })
        assertEquals("png", p.file("my-game", "/img/a.png")!!.readText())
        assertNull(p.file("my-game", "../my-game/index.html"))
        assertNull(p.file("my-game", "nope.js"))
    }

    @Test fun rejectsZipSlip() {
        val root = tmp.newFolder("apps")
        val p = AppPackages(root)
        val evil = zip("manifest.json" to manifest(), "index.html" to "x", "../../outside.txt" to "pwned")
        assertThrows(InvalidPackageException::class.java) { p.install(ByteArrayInputStream(evil)) }
        assertFalse(File(root.parentFile, "outside.txt").exists())
        assertTrue(p.list().isEmpty())
        assertTrue("временные папки удалены", root.listFiles()!!.isEmpty())
    }

    @Test fun rejectsPackageWithoutEntry() {
        val p = AppPackages(tmp.newFolder("apps"))
        assertThrows(InvalidPackageException::class.java) { p.install(ByteArrayInputStream(zip("manifest.json" to manifest()))) }
        assertThrows(InvalidPackageException::class.java) { p.install(ByteArrayInputStream(zip("index.html" to "x"))) }
    }

    @Test fun updateReplacesOldFiles() {
        val p = AppPackages(tmp.newFolder("apps"))
        p.install(ByteArrayInputStream(zip("manifest.json" to manifest(), "index.html" to "v1", "old.js" to "x")))
        val bad = zip("manifest.json" to manifest(version = "2.0.0"), "index.html" to "v2", "../x" to "y")
        assertThrows(InvalidPackageException::class.java) { p.install(ByteArrayInputStream(bad)) }
        assertEquals("неудачное обновление не трогает установленную версию", "v1", p.file("my-game", "index.html")!!.readText())

        p.install(ByteArrayInputStream(zip("manifest.json" to manifest(version = "2.0.0"), "index.html" to "v2")))
        assertEquals("2.0.0", p.get("my-game")!!.version)
        assertEquals("v2", p.file("my-game", "index.html")!!.readText())
        assertNull(p.file("my-game", "old.js"))
    }

    @Test fun inspectReadsManifestOnly() {
        val p = AppPackages(tmp.newFolder("apps"))
        val m = p.inspect(ByteArrayInputStream(zip("index.html" to "x", "manifest.json" to manifest(id = "abc"))))
        assertEquals("abc", m.id)
        assertTrue(p.list().isEmpty())
    }

    // ------------------------------------------------------------ рекорды и разрешения

    @Test fun scoresHigherIsBetter() {
        val st = AppState(tmp.newFolder("state"), AppManifest.parse(manifest()))
        assertTrue(st.submit(10.0, "Аня", now = 1).isRecord)
        assertFalse(st.submit(5.0, "Боря", now = 2).isRecord)
        val r = st.submit(20.0, "Вова", now = 3)
        assertTrue(r.isRecord)
        assertEquals(1, r.rank)
        assertEquals(listOf(20.0, 10.0, 5.0), st.top().map { it.score })
    }

    @Test fun scoresLowerIsBetterAndLevels() {
        val dir = tmp.newFolder("state")
        val m = AppManifest.parse(manifest(extra = ""","scores":{"order":"asc"}"""))
        val st = AppState(dir, m)
        st.submit(30.5, "A", "1", now = 1)
        val r = st.submit(25.0, "B", "1", now = 2)
        assertTrue(r.isRecord)
        st.submit(99.0, "C", "2", now = 3)
        assertEquals(listOf(25.0, 30.5), st.top(level = "1").map { it.score })
        assertEquals(99.0, st.best("2")!!.score, 0.0)
        // сохраняется на диск
        assertEquals(3, AppState(dir, m).scores().size)
    }

    @Test fun permissionsRememberedAndRequireManifest() {
        val st = AppState(tmp.newFolder("state"), AppManifest.parse("""{"id":"cam","name":"Камера","permissions":["camera","sensors"]}"""))
        assertNull(st.permission("camera"))
        assertFalse(st.allowed("camera"))
        st.setPermission("camera", true)
        assertTrue(st.allowed("camera"))
        assertTrue(st.allowed("sensors"))
        assertFalse("не объявлено в манифесте", st.allowed("microphone"))
        st.clearPermission("camera")
        assertNull(st.permission("camera"))
        assertNotNull(st.manifest)
    }
}
