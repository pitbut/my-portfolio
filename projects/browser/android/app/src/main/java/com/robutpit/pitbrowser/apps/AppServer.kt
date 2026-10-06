package com.robutpit.pitbrowser.apps

import android.content.Context
import android.net.Uri
import android.webkit.WebResourceResponse
import java.io.ByteArrayInputStream
import java.io.FileInputStream

/**
 * Отдаёт файлы установленного приложения по адресу https://<id>.pitapp.robutpit.com/...
 * прямо с телефона — без интернета. Адрес https нужен, чтобы работали камера, датчики и т.п.
 */
class AppServer(private val context: Context, private val manifest: AppManifest) {

    private val host = "${manifest.id}.${AppManifest.APP_DOMAIN}"

    fun isAppUrl(uri: Uri) = uri.scheme == "https" && uri.host == host

    fun serve(uri: Uri): WebResourceResponse {
        val path = uri.path.orEmpty().trimStart('/')
        // PitSDK всегда отдаёт браузер — у приложения не может быть устаревшей или подменённой версии.
        if (path == "pit.js" || path.endsWith("/pit.js")) {
            return response("text/javascript", context.assets.open("pit/pit.js"))
        }
        val file = Apps.packages(context).file(manifest.id, path.ifEmpty { manifest.entry })
            ?: return error(404, "Not Found")
        return response(mimeOf(file.name), FileInputStream(file))
    }

    private fun response(mime: String, data: java.io.InputStream) =
        WebResourceResponse(mime, if (mime.startsWith("text/") || mime.endsWith("json") || mime.endsWith("javascript")) "utf-8" else null, 200, "OK",
            mapOf("Cache-Control" to "no-cache", "X-Content-Type-Options" to "nosniff"), data)

    companion object {
        private val MIME = mapOf(
            "html" to "text/html", "htm" to "text/html", "js" to "text/javascript", "mjs" to "text/javascript",
            "css" to "text/css", "json" to "application/json", "txt" to "text/plain", "xml" to "application/xml",
            "png" to "image/png", "jpg" to "image/jpeg", "jpeg" to "image/jpeg", "gif" to "image/gif",
            "webp" to "image/webp", "svg" to "image/svg+xml", "ico" to "image/x-icon", "avif" to "image/avif",
            "mp3" to "audio/mpeg", "ogg" to "audio/ogg", "oga" to "audio/ogg", "wav" to "audio/wav", "m4a" to "audio/mp4",
            "mp4" to "video/mp4", "webm" to "video/webm",
            "woff" to "font/woff", "woff2" to "font/woff2", "ttf" to "font/ttf", "otf" to "font/otf",
            "wasm" to "application/wasm", "glb" to "model/gltf-binary", "gltf" to "model/gltf+json",
            "bin" to "application/octet-stream", "data" to "application/octet-stream",
        )

        fun mimeOf(name: String) = MIME[name.substringAfterLast('.', "").lowercase()] ?: "application/octet-stream"

        fun error(code: Int, reason: String) =
            WebResourceResponse("text/plain", "utf-8", code, reason, emptyMap(), ByteArrayInputStream(reason.toByteArray()))
    }
}
