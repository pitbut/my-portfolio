package com.robutpit.pitbrowser.apps

import java.io.File
import java.io.InputStream
import java.util.zip.ZipInputStream

/**
 * Установленные приложения: root/<id>/ — файлы пакета, root/<id>/manifest.json — манифест.
 * Пакет .pitapp — обычный zip с manifest.json в корне.
 */
class AppPackages(private val root: File) {

    init { root.mkdirs() }

    fun list(): List<AppManifest> = root.listFiles { f -> f.isDirectory && !f.name.startsWith(".") }
        .orEmpty()
        .mapNotNull { dir -> runCatching { AppManifest.parse(File(dir, MANIFEST).readText()) }.getOrNull()?.takeIf { it.id == dir.name } }
        .sortedBy { installedAt(it.id) }

    fun get(id: String): AppManifest? = list().find { it.id == id }

    fun dir(id: String) = File(root, id)

    private fun installedAt(id: String) = File(root, "$id/$MANIFEST").lastModified()

    /** Файл пакета по пути из URL; null — если его нет или путь выходит за пределы приложения. */
    fun file(id: String, path: String): File? {
        val clean = path.trimStart('/').ifEmpty { return null }
        if (!AppManifest.isSafePath(clean)) return null
        val base = dir(id).canonicalFile
        val f = File(base, clean).canonicalFile
        return f.takeIf { it.isFile && it.path.startsWith(base.path + File.separator) }
    }

    /** Читает пакет, не распаковывая на диск: только проверка манифеста (для окна «Установить?»). */
    fun inspect(input: InputStream): AppManifest {
        ZipInputStream(input.buffered()).use { zip ->
            while (true) {
                val e = zip.nextEntry ?: break
                if (e.name.trimStart('/') == MANIFEST) return AppManifest.parse(String(readLimited(zip, MAX_MANIFEST), Charsets.UTF_8))
            }
        }
        throw InvalidPackageException("в пакете нет manifest.json")
    }

    /**
     * Устанавливает или обновляет приложение. Сначала распаковывает во временную папку,
     * проверяет, и только потом заменяет старую версию — сбой не ломает установленное.
     */
    fun install(input: InputStream): AppManifest {
        val tmp = File(root, ".install-${System.nanoTime()}")
        try {
            tmp.mkdirs()
            var total = 0L
            var count = 0
            ZipInputStream(input.buffered()).use { zip ->
                while (true) {
                    val e = zip.nextEntry ?: break
                    val name = e.name.trimStart('/')
                    if (e.isDirectory) continue
                    if (!AppManifest.isSafePath(name)) throw InvalidPackageException("недопустимый путь в архиве: «${e.name}»")
                    if (++count > MAX_FILES) throw InvalidPackageException("слишком много файлов (больше $MAX_FILES)")
                    val out = File(tmp, name)
                    out.parentFile?.mkdirs()
                    out.outputStream().use { os ->
                        val buf = ByteArray(64 * 1024)
                        while (true) {
                            val n = zip.read(buf)
                            if (n < 0) break
                            total += n
                            if (total > MAX_SIZE) throw InvalidPackageException("пакет больше ${MAX_SIZE / 1024 / 1024} МБ")
                            os.write(buf, 0, n)
                        }
                    }
                }
            }
            val mf = File(tmp, MANIFEST).takeIf { it.isFile } ?: throw InvalidPackageException("в пакете нет manifest.json")
            val manifest = AppManifest.parse(mf.readText())
            if (!File(tmp, manifest.entry).isFile) throw InvalidPackageException("нет стартового файла ${manifest.entry}")
            manifest.icon?.let { if (!File(tmp, it).isFile) throw InvalidPackageException("нет иконки $it") }

            val target = dir(manifest.id)
            val old = File(root, ".old-${manifest.id}-${System.nanoTime()}")
            if (target.exists() && !target.renameTo(old)) throw InvalidPackageException("не удалось обновить приложение")
            if (!tmp.renameTo(target)) { old.renameTo(target); throw InvalidPackageException("не удалось установить приложение") }
            old.deleteRecursively()
            return manifest
        } finally {
            tmp.deleteRecursively()
        }
    }

    fun uninstall(id: String) {
        if (AppManifest.isSafePath(id) && !id.contains('/')) dir(id).deleteRecursively()
    }

    private fun readLimited(input: InputStream, limit: Int): ByteArray {
        val out = java.io.ByteArrayOutputStream()
        val buf = ByteArray(8192)
        while (true) {
            val n = input.read(buf)
            if (n < 0) break
            out.write(buf, 0, n)
            if (out.size() > limit) throw InvalidPackageException("manifest.json слишком большой")
        }
        return out.toByteArray()
    }

    companion object {
        const val MANIFEST = "manifest.json"
        const val MAX_SIZE = 200L * 1024 * 1024
        const val MAX_FILES = 5000
        private const val MAX_MANIFEST = 64 * 1024
    }
}
