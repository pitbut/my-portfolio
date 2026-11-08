package com.robutpit.screentranslator

import android.accessibilityservice.AccessibilityServiceInfo
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.view.View
import android.view.accessibility.AccessibilityManager
import android.widget.AdapterView
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.EditText
import android.widget.Spinner
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.google.android.material.materialswitch.MaterialSwitch
import com.google.android.material.slider.Slider
import com.google.mlkit.common.model.RemoteModelManager
import com.google.mlkit.nl.translate.TranslateRemoteModel
import kotlinx.coroutines.launch
import kotlinx.coroutines.tasks.await

class MainActivity : AppCompatActivity() {

    private lateinit var prefs: Prefs
    private val engine by lazy { TranslationEngine() }

    private val ocrScripts = listOf(
        "latin" to "Латиница (английский, немецкий, испанский…)",
        "chinese" to "Китайский",
        "japanese" to "Японский",
        "korean" to "Корейский",
    )

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        prefs = Prefs(this)

        findViewById<Button>(R.id.btnAccessibility).setOnClickListener {
            startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS))
        }
        findViewById<Button>(R.id.btnAppInfo).setOnClickListener {
            startActivity(
                Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:$packageName"))
            )
        }

        val langNames = Languages.all.map { it.second }
        val codes = Languages.all.map { it.first }
        setupSpinner(R.id.spTarget, langNames, codes.indexOf(prefs.target)) {
            prefs.target = codes[it]; refreshModels()
        }
        setupSpinner(R.id.spFallback, langNames, codes.indexOf(prefs.fallbackSource)) {
            prefs.fallbackSource = codes[it]
        }
        setupSpinner(R.id.spOcr, ocrScripts.map { it.second }, ocrScripts.indexOfFirst { it.first == prefs.ocrScript }) {
            prefs.ocrScript = ocrScripts[it].first
        }

        bindSwitch(R.id.swEnabled, prefs.enabled) { prefs.enabled = it }
        bindSwitch(R.id.swBubble, prefs.showBubble) { prefs.showBubble = it }
        bindSwitch(R.id.swDark, prefs.darkStyle) { prefs.darkStyle = it }
        bindSwitch(R.id.swAutoOcr, prefs.autoOcr) { prefs.autoOcr = it }
        if (Build.VERSION.SDK_INT < 30) {
            findViewById<MaterialSwitch>(R.id.swAutoOcr).apply { isEnabled = false; text = "$text (нужен Android 11+)" }
        }

        val scaleLabel = findViewById<TextView>(R.id.scaleLabel)
        findViewById<Slider>(R.id.slScale).apply {
            value = (Math.round(prefs.textScale * 10) / 10f).coerceIn(valueFrom, valueTo)
            scaleLabel.text = "Размер текста перевода: ${(value * 100).toInt()}%"
            addOnChangeListener { _, v, fromUser ->
                scaleLabel.text = "Размер текста перевода: ${(v * 100).toInt()}%"
                if (fromUser) prefs.textScale = v
            }
        }

        findViewById<Button>(R.id.btnDownload).setOnClickListener { downloadModels() }
        findViewById<Button>(R.id.btnClearExcluded).setOnClickListener {
            prefs.excluded = emptySet(); refreshExcluded()
        }
        findViewById<Button>(R.id.btnTest).setOnClickListener { testTranslate() }
    }

    override fun onResume() {
        super.onResume()
        refreshService()
        refreshModels()
        refreshExcluded()
        findViewById<MaterialSwitch>(R.id.swBubble).isChecked = prefs.showBubble
        findViewById<MaterialSwitch>(R.id.swEnabled).isChecked = prefs.enabled
    }

    private fun isServiceEnabled(): Boolean {
        val am = getSystemService(ACCESSIBILITY_SERVICE) as AccessibilityManager
        return am.getEnabledAccessibilityServiceList(AccessibilityServiceInfo.FEEDBACK_ALL_MASK)
            .any { it.resolveInfo.serviceInfo.packageName == packageName }
    }

    private fun refreshService() {
        val on = isServiceEnabled()
        findViewById<TextView>(R.id.serviceStatus).text =
            if (on) "✅ Служба перевода включена" else "⚠️ Служба перевода выключена"
        findViewById<TextView>(R.id.serviceHint).text = if (on)
            "Откройте любое приложение — перевод появится поверх текста. Синяя кнопка с кодом языка переключает перевод и оригинал."
        else
            "1. Нажмите кнопку ниже.\n2. Найдите «Экранный переводчик» (иногда в разделе «Скачанные приложения»).\n3. Включите переключатель и подтвердите.\n\nНа Android 13+ переключатель для приложений, установленных из APK, может быть серым: откройте «О приложении» → ⋮ (три точки вверху) → «Разрешить ограниченные настройки», затем вернитесь сюда."
        findViewById<View>(R.id.btnAccessibility).visibility = View.VISIBLE
        findViewById<View>(R.id.btnAppInfo).visibility =
            if (!on && Build.VERSION.SDK_INT >= 33) View.VISIBLE else View.GONE
    }

    private fun refreshModels() {
        val info = findViewById<TextView>(R.id.modelsInfo)
        lifecycleScope.launch {
            val models = try {
                RemoteModelManager.getInstance().getDownloadedModels(TranslateRemoteModel::class.java).await()
            } catch (e: Exception) {
                emptySet()
            }
            val names = models.map { Languages.name(it.language) }.sorted()
            info.text = if (names.isEmpty()) "Модели ещё не скачаны — они загрузятся сами при первом переводе."
            else "Скачано: " + names.joinToString(", ")
        }
    }

    private fun downloadModels() {
        val btn = findViewById<Button>(R.id.btnDownload)
        btn.isEnabled = false
        btn.text = "Загрузка… (около 30 МБ на язык)"
        lifecycleScope.launch {
            val ok = engine.prepare(prefs.fallbackSource, prefs.target)
            btn.isEnabled = true
            btn.text = if (ok) "Готово ✓ Скачать ещё раз" else "Ошибка загрузки — проверьте интернет и повторите"
            refreshModels()
        }
    }

    private fun refreshExcluded() {
        val ex = prefs.excluded
        findViewById<TextView>(R.id.excludedInfo).text = if (ex.isEmpty())
            "Пусто. Чтобы отключить перевод в каком-то приложении, откройте его и удержите плавающую кнопку → «Не переводить в…»."
        else ex.joinToString("\n") { "• " + appLabel(it) }
        findViewById<View>(R.id.btnClearExcluded).visibility = if (ex.isEmpty()) View.GONE else View.VISIBLE
    }

    private fun appLabel(pkg: String) = try {
        packageManager.getApplicationLabel(packageManager.getApplicationInfo(pkg, 0)).toString()
    } catch (_: Exception) {
        pkg
    }

    private fun testTranslate() {
        val text = findViewById<EditText>(R.id.etTest).text?.toString()?.trim().orEmpty()
        val out = findViewById<TextView>(R.id.testResult)
        if (text.isEmpty()) return
        out.text = "Перевожу… (первый раз скачивается модель языка)"
        lifecycleScope.launch {
            val src = engine.detect(text).takeIf { it != TranslationEngine.UNKNOWN } ?: prefs.fallbackSource
            val res = engine.translate(text, src, prefs.target)
            out.text = when {
                src == prefs.target -> "Текст уже на языке «${Languages.name(src)}»."
                res == null -> "Не удалось перевести — нужен интернет, чтобы один раз скачать модель."
                else -> "${Languages.name(src)} → ${Languages.name(prefs.target)}:\n$res"
            }
            refreshModels()
        }
    }

    private fun setupSpinner(id: Int, items: List<String>, selected: Int, onSelect: (Int) -> Unit) {
        val sp = findViewById<Spinner>(id)
        sp.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, items)
        if (selected >= 0) sp.setSelection(selected, false)
        sp.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(p: AdapterView<*>?, v: View?, pos: Int, id: Long) {
                if (pos != selected || sp.tag != null) onSelect(pos)
                sp.tag = true
            }

            override fun onNothingSelected(p: AdapterView<*>?) {}
        }
    }

    private fun bindSwitch(id: Int, value: Boolean, onChange: (Boolean) -> Unit) {
        findViewById<MaterialSwitch>(id).apply {
            isChecked = value
            setOnCheckedChangeListener { _, c -> onChange(c) }
        }
    }

    override fun onDestroy() {
        engine.close()
        super.onDestroy()
    }
}
