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
 * Ключи ИИ-сервисов: шифруются ключом из Android Keystore (аппаратное хранилище там, где оно есть).
 * Ни страницы, ни приложения, ни сами агенты их не видят — только маску sk-…xyz.
 */
object KeyVault {
    private const val ALIAS = "pitbrowser_agents_key"
    private const val PREFS = "pit_agents_secret"

    /** Ключ Claude хранится под старым именем — чтобы не потерять его при обновлении с 1.6. */
    private fun name(provider: String) = if (provider == Provider.CLAUDE) "key" else "key_$provider"

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

    fun save(context: Context, apiKey: String, provider: String = Provider.CLAUDE) {
        val c = Cipher.getInstance("AES/GCM/NoPadding")
        c.init(Cipher.ENCRYPT_MODE, secretKey())
        val blob = Base64.encodeToString(c.iv, Base64.NO_WRAP) + ":" +
            Base64.encodeToString(c.doFinal(apiKey.toByteArray(Charsets.UTF_8)), Base64.NO_WRAP)
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putString(name(provider), blob).apply()
    }

    fun load(context: Context, provider: String = Provider.CLAUDE): String? {
        val blob = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(name(provider), null) ?: return null
        return runCatching {
            val (iv, data) = blob.split(":").let { Base64.decode(it[0], Base64.NO_WRAP) to Base64.decode(it[1], Base64.NO_WRAP) }
            val c = Cipher.getInstance("AES/GCM/NoPadding")
            c.init(Cipher.DECRYPT_MODE, secretKey(), GCMParameterSpec(128, iv))
            String(c.doFinal(data), Charsets.UTF_8)
        }.getOrElse { clear(context, provider); null } // например, после восстановления из резервной копии на другом телефоне
    }

    fun clear(context: Context, provider: String = Provider.CLAUDE) =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().remove(name(provider)).apply()

    fun masked(key: String) = if (key.length > 12) key.take(7) + "…" + key.takeLast(4) else "…"
}

/** Запуски агентов и команд: до MAX_PARALLEL одновременно, в фоне; живые события — подписчикам (экран агентов). */
object Agents {
    private const val CHANNEL = "agents"
    const val MAX_PARALLEL = 3
    private val executor = Executors.newCachedThreadPool()
    private val listeners = mutableSetOf<(JSONObject) -> Unit>()
    @Volatile private var store: AgentStore? = null
    @Volatile private var providers: ProviderStore? = null

    private class Running(@Volatile var run: AgentRun, val cancel: AtomicBoolean, val kind: String)
    private val running = java.util.concurrent.ConcurrentHashMap<String, Running>()
    @Volatile var screenVisible = false

    fun store(context: Context): AgentStore =
        store ?: synchronized(this) { store ?: AgentStore(java.io.File(context.filesDir, "agents")).also { store = it } }

    fun providers(context: Context): ProviderStore =
        providers ?: synchronized(this) { providers ?: ProviderStore(java.io.File(context.filesDir, "agents")).also { providers = it } }

    fun listen(l: (JSONObject) -> Unit) = synchronized(listeners) { listeners += l }
    fun unlisten(l: (JSONObject) -> Unit) = synchronized(listeners) { listeners -= l }
    private fun emit(e: JSONObject) = synchronized(listeners) { listeners.toList() }.forEach { runCatching { it(e) } }

    /** Что сейчас работает (для экрана): запуски агентов и команд. */
    fun runningRuns(): List<AgentRun> = running.values.map { it.run }

    // ------------------------------------------------------------ лимит токенов в день

    private fun prefs(c: Context) = c.getSharedPreferences("pit_agents", Context.MODE_PRIVATE)
    fun dailyLimit(c: Context) = prefs(c).getLong("dailyLimit", 1_000_000L)
    fun setDailyLimit(c: Context, v: Long) = prefs(c).edit().putLong("dailyLimit", v.coerceIn(10_000L, 50_000_000L)).apply()

    fun startOfToday(): Long = Calendar.getInstance().apply {
        set(Calendar.HOUR_OF_DAY, 0); set(Calendar.MINUTE, 0); set(Calendar.SECOND, 0); set(Calendar.MILLISECOND, 0)
    }.timeInMillis

    fun todayTokens(c: Context) = store(c).tokensSince(startOfToday())

    // ------------------------------------------------------------ движки разных ИИ

    /** Есть ли ключ (у своего сервера без ключа — считаем, что есть). */
    fun hasKey(c: Context, p: Provider) = KeyVault.load(c, p.id) != null || (!p.builtIn && p.kind == "openai")

    fun engineFor(c: Context, agent: Agent): Engine {
        val p = providers(c).get(agent.provider) ?: throw IllegalStateException("ИИ-сервис «${agent.provider}» удалён — выберите другой у агента «${agent.name}»")
        return if (p.kind == "anthropic") {
            AgentRunner(KeyVault.load(c, p.id) ?: throw IllegalStateException("добавьте ключ ${p.name} в разделе «ИИ»"))
        } else {
            val key = KeyVault.load(c, p.id) ?: if (!p.builtIn) "none" else throw IllegalStateException("добавьте ключ ${p.name} в разделе «ИИ»")
            OpenAiEngine(p, key)
        }
    }

    /** Поиск для ИИ без встроенного: через Claude, если его ключ добавлен. */
    private fun webSearch(c: Context): ((String) -> WebSearchResult)? {
        val key = KeyVault.load(c, Provider.CLAUDE) ?: return null
        val model = providers(c).get(Provider.CLAUDE)?.model?.takeIf { it.startsWith("claude-") } ?: Agent.MODELS.keys.first()
        return { q -> AgentRunner(key).searchFor(q, model) }
    }

    private fun device(app: Context) = object : Device {
        override fun notify(title: String, text: String) = post(app, title, text)
    }

    private fun checkCanStart(app: Context) {
        if (running.size >= MAX_PARALLEL) throw IllegalStateException("уже работают $MAX_PARALLEL запуска — дождитесь или остановите один")
        if (todayTokens(app) >= dailyLimit(app)) throw IllegalStateException("дневной лимит токенов исчерпан — увеличьте его или подождите до завтра")
    }

    // ------------------------------------------------------------ запуск агента

    fun start(context: Context, agentId: String): String {
        val app = context.applicationContext
        val agent = store(app).get(agentId) ?: throw IllegalStateException("агент не найден")
        checkCanStart(app)
        val engine = engineFor(app, agent) // заранее: нет ключа — сразу понятная ошибка
        val cancel = AtomicBoolean(false)
        val placeholder = AgentRun(agent.id, System.currentTimeMillis(), model = agent.model, provider = agent.provider, title = agent.name)
        val slot = Running(placeholder, cancel, "agent")
        running[placeholder.runId] = slot
        emit(JSONObject().put("type", "run").put("run", placeholder.toJson()))
        executor.execute {
            val ctx = RunContext(device(app), cancel, { r -> slot.run = r; emit(JSONObject().put("type", "run").put("run", r.toJson().put("runId", placeholder.runId))) }, webSearch = webSearch(app))
            val run = try { engine.run(agent, agent.task, ctx) } catch (e: Exception) {
                placeholder.apply { status = "error"; error = e.message ?: e.toString(); finished = System.currentTimeMillis() }
            }
            finish(app, placeholder.runId, run, agent.name)
        }
        return placeholder.runId
    }

    // ------------------------------------------------------------ запуск команды

    fun startTeam(context: Context, teamId: String): String {
        val app = context.applicationContext
        val team = store(app).team(teamId) ?: throw IllegalStateException("команда не найдена")
        val agents = store(app).agents()
        checkCanStart(app)
        // ключи всех участников проверяем до запуска, а не посреди работы
        (team.members + team.judge).filter { it.isNotEmpty() }.forEach { id ->
            agents.find { it.id == id }?.let { engineFor(app, it) }
        }
        val cancel = AtomicBoolean(false)
        val placeholder = AgentRun(team.id, System.currentTimeMillis(), provider = "team", title = team.name)
        val slot = Running(placeholder, cancel, "team")
        running[placeholder.runId] = slot
        emit(JSONObject().put("type", "run").put("run", placeholder.toJson()))
        executor.execute {
            val runner = TeamRunner(
                engineFor = { a -> engineFor(app, a) },
                contextFor = { onStep, helpers, ask -> RunContext(device(app), cancel, onStep, helpers, ask, webSearch(app)) },
            )
            val run = try {
                runner.run(team, agents) { r -> slot.run = r; emit(JSONObject().put("type", "run").put("run", r.toJson().put("runId", placeholder.runId))) }
            } catch (e: Exception) {
                placeholder.apply { status = "error"; error = e.message ?: e.toString(); finished = System.currentTimeMillis() }
            }
            finish(app, placeholder.runId, run, "Команда «${team.name}»")
        }
        return placeholder.runId
    }

    private fun finish(app: Context, runId: String, run: AgentRun, who: String) {
        val stored = AgentRun.parse(run.toJson().put("runId", runId))
        store(app).addRun(stored)
        running.remove(runId)
        emit(JSONObject().put("type", "finished").put("run", stored.toJson()))
        if (!screenVisible) {
            val what = when (run.status) {
                "done" -> "Готово: " + run.result.lineSequence().firstOrNull { it.isNotBlank() }.orEmpty().trimStart('#', ' ').take(120)
                "stopped" -> "Остановлен"
                else -> "Ошибка: " + run.error.take(120)
            }
            post(app, who, what)
        }
    }

    fun stop(runId: String) { running[runId]?.cancel?.set(true) }
    fun stopAll() = running.values.forEach { it.cancel.set(true) }

    // ------------------------------------------------------------ ключи и модели

    /** Проверить ключ и получить список моделей сервиса — в фоне. done(модели или null, ошибка или null). */
    fun checkKey(context: Context, providerId: String, done: (List<String>?, String?) -> Unit) {
        val app = context.applicationContext
        executor.execute {
            val p = providers(app).get(providerId)
            if (p == null) { done(null, "нет такого сервиса"); return@execute }
            val key = KeyVault.load(app, p.id) ?: if (!p.builtIn) "none" else null
            if (key == null) { done(null, "ключ не добавлен"); return@execute }
            val r = runCatching {
                if (p.kind == "anthropic") AgentRunner(key).listModels().filter { it.startsWith("claude-") }
                else OpenAiEngine(p, key).listModels()
            }
            done(r.getOrNull(), r.exceptionOrNull()?.let { e ->
                when (e) {
                    is com.anthropic.errors.UnauthorizedException -> "ключ не подходит"
                    is OpenAiEngine.ApiException -> if (e.code == 401) "ключ не подходит" else "сервис ответил ошибкой ${e.code}: ${e.message?.take(150)}"
                    else -> "не удалось проверить: ${e.message?.take(150)}"
                }
            })
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
        nm.notify((System.nanoTime() % 1_000_000).toInt(), n)
    }
}
