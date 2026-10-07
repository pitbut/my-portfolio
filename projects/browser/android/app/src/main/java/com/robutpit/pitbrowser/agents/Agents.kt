package com.robutpit.pitbrowser.agents

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import com.robutpit.pitbrowser.AgentsActivity
import com.robutpit.pitbrowser.R
import org.json.JSONObject
import java.security.KeyStore
import java.util.Calendar
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/**
 * Ключ Claude API: шифруется ключом из Android Keystore (аппаратное хранилище там, где оно есть).
 * Ни страницы, ни приложения, ни сами агенты его не видят — только маску sk-…xyz.
 */
object KeyVault {
    private const val ALIAS = "pitbrowser_agents_key"
    private const val PREFS = "pit_agents_secret"

    private fun secretKey(): SecretKey {
        val ks = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        (ks.getEntry(ALIAS, null) as? KeyStore.SecretKeyEntry)?.let { return it.secretKey }
        val gen = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore")
        gen.init(
            KeyGenParameterSpec.Builder(ALIAS, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setKeySize(256)
                .build(),
        )
        return gen.generateKey()
    }

    fun save(context: Context, apiKey: String) {
        val c = Cipher.getInstance("AES/GCM/NoPadding")
        c.init(Cipher.ENCRYPT_MODE, secretKey())
        val blob = Base64.encodeToString(c.iv, Base64.NO_WRAP) + ":" +
            Base64.encodeToString(c.doFinal(apiKey.toByteArray(Charsets.UTF_8)), Base64.NO_WRAP)
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putString("key", blob).apply()
    }

    fun load(context: Context): String? {
        val blob = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString("key", null) ?: return null
        return runCatching {
            val (iv, data) = blob.split(":").let { Base64.decode(it[0], Base64.NO_WRAP) to Base64.decode(it[1], Base64.NO_WRAP) }
            val c = Cipher.getInstance("AES/GCM/NoPadding")
            c.init(Cipher.DECRYPT_MODE, secretKey(), GCMParameterSpec(128, iv))
            String(c.doFinal(data), Charsets.UTF_8)
        }.getOrElse { clear(context); null } // например, после восстановления из резервной копии на другом телефоне
    }

    fun clear(context: Context) = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().remove("key").apply()

    fun masked(key: String) = if (key.length > 12) key.take(7) + "…" + key.takeLast(4) else "…"
}

/** Запуски агентов: один за раз, в фоновом потоке; живые события — подписчикам (экран агентов). */
object Agents {
    private const val CHANNEL = "agents"
    private val executor = Executors.newSingleThreadExecutor()
    private val listeners = mutableSetOf<(JSONObject) -> Unit>()
    @Volatile private var store: AgentStore? = null
    @Volatile var current: AgentRun? = null
        private set
    private var cancel = AtomicBoolean(false)
    @Volatile var screenVisible = false

    fun store(context: Context): AgentStore =
        store ?: synchronized(this) { store ?: AgentStore(java.io.File(context.filesDir, "agents")).also { store = it } }

    fun listen(l: (JSONObject) -> Unit) = synchronized(listeners) { listeners += l }
    fun unlisten(l: (JSONObject) -> Unit) = synchronized(listeners) { listeners -= l }
    private fun emit(e: JSONObject) = synchronized(listeners) { listeners.toList() }.forEach { it(e) }

    // ------------------------------------------------------------ лимит токенов в день

    private fun prefs(c: Context) = c.getSharedPreferences("pit_agents", Context.MODE_PRIVATE)
    fun dailyLimit(c: Context) = prefs(c).getLong("dailyLimit", 1_000_000L)
    fun setDailyLimit(c: Context, v: Long) = prefs(c).edit().putLong("dailyLimit", v.coerceIn(10_000L, 50_000_000L)).apply()

    fun startOfToday(): Long = Calendar.getInstance().apply {
        set(Calendar.HOUR_OF_DAY, 0); set(Calendar.MINUTE, 0); set(Calendar.SECOND, 0); set(Calendar.MILLISECOND, 0)
    }.timeInMillis

    fun todayTokens(c: Context) = store(c).tokensSince(startOfToday())

    // ------------------------------------------------------------ запуск

    fun start(context: Context, agentId: String) {
        val app = context.applicationContext
        val key = KeyVault.load(app) ?: throw IllegalStateException("сначала добавьте ключ Claude API")
        val agent = store(app).get(agentId) ?: throw IllegalStateException("агент не найден")
        if (current != null) throw IllegalStateException("уже работает другой агент — дождитесь или остановите его")
        if (todayTokens(app) >= dailyLimit(app)) throw IllegalStateException("дневной лимит токенов исчерпан — увеличьте его или подождите до завтра")
        cancel = AtomicBoolean(false)
        val flag = cancel
        val placeholder = AgentRun(agent.id, System.currentTimeMillis(), model = agent.model)
        current = placeholder
        emit(JSONObject().put("type", "run").put("run", placeholder.toJson()))
        executor.execute {
            val device = object : AgentRunner.Device {
                override fun notify(title: String, text: String) = post(app, title, text)
            }
            val run = try {
                AgentRunner(key).run(agent, device, flag) { r ->
                    current = r
                    emit(JSONObject().put("type", "run").put("run", r.toJson()))
                }
            } catch (e: Exception) {
                placeholder.apply { status = "error"; error = e.message ?: e.toString(); finished = System.currentTimeMillis() }
            }
            store(app).addRun(run)
            current = null
            emit(JSONObject().put("type", "finished").put("run", run.toJson()))
            if (!screenVisible) {
                val what = when (run.status) {
                    "done" -> "Готово: " + run.result.lineSequence().firstOrNull { it.isNotBlank() }.orEmpty().trimStart('#', ' ').take(120)
                    "stopped" -> "Остановлен"
                    else -> "Ошибка: " + run.error.take(120)
                }
                post(app, "Агент «${agent.name}»", what)
            }
        }
    }

    fun stop() = cancel.set(true)

    /** Проверить ключ (бесплатно, через Models API) — в фоне. */
    fun checkKey(context: Context, key: String, done: (String?) -> Unit) {
        executor.execute {
            val err = runCatching { AgentRunner(key).checkKey() }.exceptionOrNull()?.let {
                when (it) {
                    is com.anthropic.errors.UnauthorizedException -> "ключ не подходит"
                    is com.anthropic.errors.PermissionDeniedException -> "у ключа нет доступа к моделям"
                    else -> "не удалось проверить: ${it.message?.take(150)}"
                }
            }
            done(err)
        }
    }

    // ------------------------------------------------------------ уведомления

    fun canNotify(c: Context) =
        Build.VERSION.SDK_INT < 33 || c.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED

    private fun post(c: Context, title: String, text: String) {
        if (!canNotify(c)) return
        val nm = c.getSystemService(NotificationManager::class.java) ?: return
        if (Build.VERSION.SDK_INT >= 26 && nm.getNotificationChannel(CHANNEL) == null) {
            nm.createNotificationChannel(NotificationChannel(CHANNEL, "Агенты", NotificationManager.IMPORTANCE_DEFAULT))
        }
        val open = PendingIntent.getActivity(c, 0, Intent(c, AgentsActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
        val b = if (Build.VERSION.SDK_INT >= 26) android.app.Notification.Builder(c, CHANNEL)
        else @Suppress("DEPRECATION") android.app.Notification.Builder(c)
        val n = b.setSmallIcon(R.drawable.ic_agent)
            .setContentTitle(title)
            .setContentText(text)
            .setStyle(android.app.Notification.BigTextStyle().bigText(text))
            .setContentIntent(open)
            .setAutoCancel(true)
            .build()
        nm.notify((System.currentTimeMillis() % 100000).toInt(), n)
    }
}
