package ru.rynok.app.data.remote

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import ru.rynok.app.BuildConfig
import java.io.File
import java.io.IOException

data class FamilyCreated(val familyId: String, val code: String)

/** HTTP-часть протокола: создание/присоединение к семье и загрузка медиафайлов чата. */
class RelayApi(private val httpClient: OkHttpClient = OkHttpClient()) {

    private val baseUrl = BuildConfig.RELAY_HTTP_URL

    suspend fun createFamily(): Result<FamilyCreated> = withContext(Dispatchers.IO) {
        runCatching {
            val request = Request.Builder()
                .url("$baseUrl/api/family")
                .post("".toRequestBody("application/json".toMediaType()))
                .build()
            httpClient.newCall(request).execute().use { response ->
                if (!response.isSuccessful) throw IOException("HTTP ${response.code}")
                val json = JSONObject(response.body?.string().orEmpty())
                FamilyCreated(json.getString("familyId"), json.getString("code"))
            }
        }
    }

    suspend fun joinFamily(code: String): Result<String> = withContext(Dispatchers.IO) {
        runCatching {
            val body = JSONObject().put("code", code).toString()
                .toRequestBody("application/json".toMediaType())
            val request = Request.Builder()
                .url("$baseUrl/api/family/join")
                .post(body)
                .build()
            httpClient.newCall(request).execute().use { response ->
                if (!response.isSuccessful) throw IOException("invite_code_not_found")
                JSONObject(response.body?.string().orEmpty()).getString("familyId")
            }
        }
    }

    suspend fun uploadMedia(file: File, mimeType: String): Result<String> = withContext(Dispatchers.IO) {
        runCatching {
            val body = MultipartBody.Builder()
                .setType(MultipartBody.FORM)
                .addFormDataPart("file", file.name, file.asRequestBody(mimeType.toMediaType()))
                .build()
            val request = Request.Builder()
                .url("$baseUrl/api/media")
                .post(body)
                .build()
            httpClient.newCall(request).execute().use { response ->
                if (!response.isSuccessful) throw IOException("HTTP ${response.code}")
                JSONObject(response.body?.string().orEmpty()).getString("mediaId")
            }
        }
    }

    suspend fun downloadMedia(mediaId: String, destination: File): Result<File> = withContext(Dispatchers.IO) {
        runCatching {
            val request = Request.Builder().url("$baseUrl/api/media/$mediaId").build()
            httpClient.newCall(request).execute().use { response ->
                if (!response.isSuccessful) throw IOException("HTTP ${response.code}")
                destination.outputStream().use { out ->
                    response.body?.byteStream()?.copyTo(out)
                }
                destination
            }
        }
    }
}
