package com.robutpit.pitbrowser.apps

import android.content.Context
import android.content.Intent
import android.content.pm.ShortcutInfo
import android.content.pm.ShortcutManager
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.drawable.Icon
import android.net.Uri
import android.os.Build
import android.util.Base64
import com.robutpit.pitbrowser.AppActivity
import java.io.File

/** Точка входа платформы приложений: установленные пакеты, их состояние, запуск. */
object Apps {
    @Volatile private var packages: AppPackages? = null

    fun packages(context: Context): AppPackages =
        packages ?: synchronized(this) {
            packages ?: AppPackages(File(context.filesDir, "apps")).also { packages = it; preinstall(context, it) }
        }

    fun state(context: Context, manifest: AppManifest) = AppState(File(context.filesDir, "app-state"), manifest)

    fun uninstall(context: Context, id: String) {
        val p = packages(context)
        p.get(id)?.let { state(context, it).delete() }
        p.uninstall(id)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N_MR1) {
            context.getSystemService(ShortcutManager::class.java)?.disableShortcuts(listOf(shortcutId(id)), "Приложение удалено")
        }
    }

    /** Приложения из assets/preinstalled ставятся при первом запуске (и обновляются с новой версией браузера). */
    private fun preinstall(context: Context, p: AppPackages) {
        val prefs = context.getSharedPreferences("pitbrowser", Context.MODE_PRIVATE)
        val version = context.packageManager.getPackageInfo(context.packageName, 0).let {
            @Suppress("DEPRECATION") if (Build.VERSION.SDK_INT >= 28) it.longVersionCode else it.versionCode.toLong()
        }
        if (prefs.getLong("preinstalledFor", -1) == version) return
        val removed = prefs.getStringSet("uninstalledPreinstalled", emptySet()).orEmpty()
        context.assets.list("preinstalled").orEmpty().filter { it.endsWith(".pitapp") }.forEach { name ->
            runCatching {
                val manifest = context.assets.open("preinstalled/$name").use { p.inspect(it) }
                val installed = p.get(manifest.id)
                if (manifest.id !in removed && (installed == null || installed.version != manifest.version)) {
                    context.assets.open("preinstalled/$name").use { p.install(it) }
                }
            }
        }
        prefs.edit().putLong("preinstalledFor", version).apply()
    }

    /** Запомнить, что пользователь сам удалил встроенное приложение — не ставить его снова. */
    fun rememberUninstalled(context: Context, id: String) {
        val prefs = context.getSharedPreferences("pitbrowser", Context.MODE_PRIVATE)
        val set = prefs.getStringSet("uninstalledPreinstalled", emptySet()).orEmpty() + id
        prefs.edit().putStringSet("uninstalledPreinstalled", set).apply()
    }

    fun launchIntent(context: Context, id: String): Intent =
        Intent(context, AppActivity::class.java)
            .setAction(Intent.ACTION_VIEW)
            .setData(Uri.parse("pitapp://$id"))
            // каждое приложение — отдельная карточка в списке недавних, как настоящее
            .addFlags(Intent.FLAG_ACTIVITY_NEW_DOCUMENT)

    fun iconBitmap(context: Context, manifest: AppManifest): Bitmap? {
        val f = manifest.icon?.let { packages(context).file(manifest.id, it) } ?: return null
        return runCatching { BitmapFactory.decodeFile(f.path) }.getOrNull()
    }

    /** Иконка для страницы главного экрана (data: URI, потому что страница не видит файлы приложения). */
    fun iconDataUri(context: Context, manifest: AppManifest): String? {
        val f = manifest.icon?.let { packages(context).file(manifest.id, it) } ?: return null
        if (f.length() > 512 * 1024) return null
        val mime = AppServer.mimeOf(f.name)
        return "data:$mime;base64," + Base64.encodeToString(f.readBytes(), Base64.NO_WRAP)
    }

    /** Ярлык приложения на рабочем столе телефона. */
    fun pinShortcut(context: Context, manifest: AppManifest): Boolean {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return false
        val sm = context.getSystemService(ShortcutManager::class.java) ?: return false
        if (!sm.isRequestPinShortcutSupported) return false
        val icon = iconBitmap(context, manifest)?.let { Icon.createWithBitmap(it) }
            ?: Icon.createWithResource(context, com.robutpit.pitbrowser.R.mipmap.ic_launcher)
        val info = ShortcutInfo.Builder(context, shortcutId(manifest.id))
            .setShortLabel(manifest.name.take(25))
            .setLongLabel(manifest.name)
            .setIcon(icon)
            .setIntent(launchIntent(context, manifest.id))
            .build()
        return sm.requestPinShortcut(info, null)
    }

    private fun shortcutId(id: String) = "app-$id"

    // --- имя игрока для таблиц рекордов (общее для всех игр)
    fun playerName(context: Context): String? =
        context.getSharedPreferences("pitbrowser", Context.MODE_PRIVATE).getString("playerName", null)

    fun setPlayerName(context: Context, name: String) =
        context.getSharedPreferences("pitbrowser", Context.MODE_PRIVATE).edit().putString("playerName", name.trim().take(30)).apply()
}
