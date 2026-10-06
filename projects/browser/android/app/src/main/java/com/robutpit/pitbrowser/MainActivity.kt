package com.robutpit.pitbrowser

import android.Manifest
import android.annotation.SuppressLint
import android.app.Activity
import android.app.AlertDialog
import android.app.DownloadManager
import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.os.Message
import android.text.Editable
import android.text.TextWatcher
import android.view.Gravity
import android.view.KeyEvent
import android.view.View
import android.view.ViewGroup
import android.view.WindowInsets
import android.view.WindowInsetsController
import android.view.inputmethod.EditorInfo
import android.view.inputmethod.InputMethodManager
import android.webkit.CookieManager
import android.webkit.GeolocationPermissions
import android.webkit.PermissionRequest
import android.webkit.URLUtil
import android.webkit.ValueCallback
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebStorage
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.ArrayAdapter
import android.widget.AutoCompleteTextView
import android.widget.BaseAdapter
import android.widget.EditText
import android.widget.Filter
import android.widget.Filterable
import android.widget.FrameLayout
import android.widget.ImageButton
import android.widget.LinearLayout
import android.widget.ListView
import android.widget.PopupMenu
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast
import org.json.JSONArray
import org.json.JSONObject

class MainActivity : Activity() {

    private class Tab(val web: WebView) {
        var title: String = "Новая вкладка"
        val url: String get() = web.url ?: ""
    }

    private lateinit var store: Store
    private lateinit var container: FrameLayout
    private lateinit var address: AutoCompleteTextView
    private lateinit var progress: ProgressBar
    private lateinit var tabCount: TextView
    private lateinit var backBtn: ImageButton
    private lateinit var forwardBtn: ImageButton
    private lateinit var findBar: View
    private lateinit var findInput: EditText
    private lateinit var findCount: TextView

    private val tabs = mutableListOf<Tab>()
    private var current: Tab? = null

    private var fileCallback: ValueCallback<Array<Uri>>? = null
    private var fullscreenView: View? = null
    private var fullscreenCallback: WebChromeClient.CustomViewCallback? = null
    private var pendingPermission: ((Boolean) -> Unit)? = null
    private var pendingDownload: (() -> Unit)? = null

    // ------------------------------------------------------------------ жизненный цикл

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        store = Store(this)

        container = findViewById(R.id.webContainer)
        address = findViewById(R.id.address)
        progress = findViewById(R.id.progress)
        tabCount = findViewById(R.id.tabCount)
        backBtn = findViewById(R.id.back)
        forwardBtn = findViewById(R.id.forward)
        findBar = findViewById(R.id.findBar)
        findInput = findViewById(R.id.findInput)
        findCount = findViewById(R.id.findCount)

        applyInsets()
        setupAddressBar()
        setupButtons()
        setupFindBar()
        CookieManager.getInstance().setAcceptCookie(true)

        val (saved, active) = store.savedTabs()
        saved.forEach { newTab(it, activate = false) }
        if (tabs.isNotEmpty()) switchTo(tabs[active.coerceIn(0, tabs.lastIndex)])
        if (!handleIntent(intent) && tabs.isEmpty()) newTab(NEW_TAB)
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        handleIntent(intent)
    }

    /** Ссылки из других приложений, «Поделиться» и веб-поиск. */
    private fun handleIntent(intent: Intent?): Boolean {
        val url = when (intent?.action) {
            Intent.ACTION_VIEW -> intent.dataString
            Intent.ACTION_WEB_SEARCH -> intent.getStringExtra("query")?.let { Omnibox.toUrl(it, store.searchEngine) }
            Intent.ACTION_SEND -> intent.getStringExtra(Intent.EXTRA_TEXT)?.let { text ->
                Regex("https?://\\S+").find(text)?.value ?: Omnibox.toUrl(text, store.searchEngine)
            }
            else -> null
        } ?: return false
        newTab(url)
        return true
    }

    override fun onPause() {
        super.onPause()
        store.saveTabs(tabs.map { it.web.url ?: NEW_TAB }, tabs.indexOf(current).coerceAtLeast(0))
        CookieManager.getInstance().flush()
        current?.web?.onPause()
    }

    override fun onResume() {
        super.onResume()
        current?.web?.onResume()
    }

    override fun onDestroy() {
        tabs.forEach { it.web.destroy() }
        super.onDestroy()
    }

    @Deprecated("Deprecated in Java")
    override fun onBackPressed() {
        val web = current?.web
        when {
            fullscreenView != null -> fullscreenCallback?.onCustomViewHidden()
            findBar.visibility == View.VISIBLE -> closeFind()
            web != null && web.canGoBack() -> web.goBack()
            tabs.size > 1 -> closeTab(current!!)
            else -> @Suppress("DEPRECATION") super.onBackPressed()
        }
    }

    /** Панели не залезают под статус-бар, вырез экрана и клавиатуру (edge-to-edge в Android 15). */
    private fun applyInsets() {
        val root = findViewById<View>(R.id.root)
        root.setOnApplyWindowInsetsListener { v, insets ->
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                val bars = insets.getInsets(WindowInsets.Type.systemBars() or WindowInsets.Type.displayCutout())
                val ime = insets.getInsets(WindowInsets.Type.ime())
                val full = fullscreenView != null
                v.setPadding(
                    if (full) 0 else bars.left, if (full) 0 else bars.top,
                    if (full) 0 else bars.right, if (full) 0 else maxOf(bars.bottom, ime.bottom),
                )
            } else {
                @Suppress("DEPRECATION")
                v.setPadding(insets.systemWindowInsetLeft, insets.systemWindowInsetTop, insets.systemWindowInsetRight, insets.systemWindowInsetBottom)
            }
            insets
        }
    }

    // ------------------------------------------------------------------ вкладки

    @SuppressLint("SetJavaScriptEnabled")
    private fun createWebView(): WebView {
        val web = WebView(this)
        with(web.settings) {
            javaScriptEnabled = true
            domStorageEnabled = true
            loadWithOverviewMode = true
            useWideViewPort = true
            builtInZoomControls = true
            displayZoomControls = false
            setSupportZoom(true)
            setSupportMultipleWindows(true)
            javaScriptCanOpenWindowsAutomatically = false
            mediaPlaybackRequiresUserGesture = true
            mixedContentMode = WebSettings.MIXED_CONTENT_COMPATIBILITY_MODE
            allowFileAccess = false
            allowContentAccess = false
            setGeolocationEnabled(true)
            userAgentString = userAgent(defaultUa = WebSettings.getDefaultUserAgent(this@MainActivity))
        }
        CookieManager.getInstance().setAcceptThirdPartyCookies(web, true)
        web.webViewClient = Client()
        web.webChromeClient = Chrome()
        web.setDownloadListener { url, userAgent, disposition, mime, _ -> download(url, userAgent, disposition, mime) }
        web.setFindListener { active, total, done -> if (done) findCount.text = if (total > 0) "${active + 1}/$total" else "0" }
        web.setOnLongClickListener { onLongPress(web) }
        return web
    }

    /** Убираем «; wv» — иначе часть сайтов отдаёт урезанную версию; в режиме ПК — десктопный UA. */
    private fun userAgent(defaultUa: String): String {
        val mobile = defaultUa.replace("; wv", "").replace(Regex("Version/\\S+ "), "")
        if (!store.desktopMode) return mobile
        val chrome = Regex("Chrome/[\\d.]+").find(mobile)?.value ?: "Chrome/130.0.0.0"
        return "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) $chrome Safari/537.36"
    }

    private fun newTab(url: String, activate: Boolean = true, after: Tab? = null): Tab {
        val tab = Tab(createWebView())
        val i = after?.let { tabs.indexOf(it) + 1 } ?: tabs.size
        tabs.add(i.coerceIn(0, tabs.size), tab)
        if (url.isNotEmpty()) tab.web.loadUrl(url)
        if (activate) switchTo(tab) else updateUi()
        return tab
    }

    private fun switchTo(tab: Tab) {
        current?.web?.let { it.onPause(); container.removeView(it) }
        current = tab
        container.addView(tab.web, FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT))
        tab.web.onResume()
        closeFind()
        updateUi()
    }

    private fun closeTab(tab: Tab) {
        val i = tabs.indexOf(tab)
        if (i < 0) return
        tabs.removeAt(i)
        if (tab == current) {
            container.removeView(tab.web)
            current = null
            if (tabs.isEmpty()) newTab(NEW_TAB) else switchTo(tabs[minOf(i, tabs.lastIndex)])
        } else updateUi()
        tab.web.destroy()
    }

    private fun updateUi() {
        val tab = current ?: return
        if (!address.hasFocus()) address.setText(displayUrl(tab.url), false)
        backBtn.isEnabled = tab.web.canGoBack()
        backBtn.alpha = if (backBtn.isEnabled) 1f else .35f
        forwardBtn.isEnabled = tab.web.canGoForward()
        forwardBtn.alpha = if (forwardBtn.isEnabled) 1f else .35f
        tabCount.text = if (tabs.size > 99) ":D" else tabs.size.toString()
    }

    private fun displayUrl(url: String) = if (url.isEmpty() || url.startsWith(NEW_TAB)) "" else url

    private fun navigate(input: String) {
        val url = Omnibox.toUrl(input, store.searchEngine) ?: return
        val tab = current
        if (tab == null) { newTab(url); return }
        tab.web.loadUrl(url)
        tab.web.requestFocus()
    }

    // ------------------------------------------------------------------ адресная строка

    private fun setupAddressBar() {
        address.setAdapter(SuggestAdapter())
        address.setOnEditorActionListener { _, action, event ->
            if (action == EditorInfo.IME_ACTION_GO || event?.keyCode == KeyEvent.KEYCODE_ENTER) {
                submitAddress(address.text.toString()); true
            } else false
        }
        address.setOnItemClickListener { parent, _, pos, _ ->
            submitAddress((parent.getItemAtPosition(pos) as Store.Entry).url)
        }
        address.setOnFocusChangeListener { _, focused ->
            if (!focused) address.setText(displayUrl(current?.url ?: ""), false)
        }
    }

    private fun submitAddress(text: String) {
        address.dismissDropDown()
        hideKeyboard()
        address.clearFocus()
        navigate(text)
    }

    private fun hideKeyboard() {
        (getSystemService(Context.INPUT_METHOD_SERVICE) as InputMethodManager)
            .hideSoftInputFromWindow(address.windowToken, 0)
    }

    private inner class SuggestAdapter : BaseAdapter(), Filterable {
        private var items: List<Store.Entry> = emptyList()
        override fun getCount() = items.size
        override fun getItem(position: Int) = items[position]
        override fun getItemId(position: Int) = position.toLong()
        override fun getView(position: Int, convertView: View?, parent: ViewGroup): View {
            val v = convertView ?: layoutInflater.inflate(android.R.layout.simple_list_item_2, parent, false)
            val e = items[position]
            v.findViewById<TextView>(android.R.id.text1).text = e.title
            v.findViewById<TextView>(android.R.id.text2).text = e.url
            return v
        }
        override fun getFilter() = object : Filter() {
            override fun performFiltering(q: CharSequence?) = FilterResults().apply {
                val list = store.suggest(q?.toString().orEmpty())
                values = list; count = list.size
            }
            @Suppress("UNCHECKED_CAST")
            override fun publishResults(q: CharSequence?, r: FilterResults?) {
                items = (r?.values as? List<Store.Entry>).orEmpty()
                if (items.isEmpty()) notifyDataSetInvalidated() else notifyDataSetChanged()
            }
            override fun convertResultToString(result: Any?) = (result as? Store.Entry)?.url ?: ""
        }
    }

    // ------------------------------------------------------------------ кнопки и меню

    private fun setupButtons() {
        findViewById<View>(R.id.reload).setOnClickListener {
            val web = current?.web ?: return@setOnClickListener
            if (progress.visibility == View.VISIBLE) web.stopLoading() else web.reload()
        }
        backBtn.setOnClickListener { current?.web?.takeIf { it.canGoBack() }?.goBack() }
        forwardBtn.setOnClickListener { current?.web?.takeIf { it.canGoForward() }?.goForward() }
        findViewById<View>(R.id.home).setOnClickListener { current?.web?.loadUrl(NEW_TAB) }
        findViewById<View>(R.id.tabsButton).setOnClickListener { showTabs() }
        findViewById<View>(R.id.tabsButton).setOnLongClickListener { newTab(NEW_TAB); focusAddress(); true }
        findViewById<View>(R.id.menu).setOnClickListener { showMenu(it) }
    }

    private fun focusAddress() {
        address.requestFocus()
        address.selectAll()
        (getSystemService(Context.INPUT_METHOD_SERVICE) as InputMethodManager).showSoftInput(address, 0)
    }

    private fun showMenu(anchor: View) {
        val tab = current
        val url = tab?.url.orEmpty()
        val isWeb = url.startsWith("http")
        val menu = PopupMenu(this, anchor)
        val m = menu.menu
        m.add(0, 1, 0, "Новая вкладка")
        if (isWeb) m.add(0, 2, 0, if (store.isBookmarked(url)) "Удалить из закладок" else "Добавить в закладки")
        m.add(0, 3, 0, "Закладки")
        m.add(0, 4, 0, "История")
        m.add(0, 5, 0, "Загрузки")
        if (isWeb) {
            m.add(0, 6, 0, "Найти на странице")
            m.add(0, 7, 0, "Поделиться")
        }
        m.add(0, 8, 0, "Версия для ПК").apply { isCheckable = true; isChecked = store.desktopMode }
        m.add(0, 9, 0, "Поисковая система")
        m.add(0, 10, 0, "Очистить данные")
        m.add(0, 11, 0, "Закрыть все вкладки")
        menu.setOnMenuItemClickListener { item ->
            when (item.itemId) {
                1 -> { newTab(NEW_TAB); focusAddress() }
                2 -> {
                    val added = store.toggleBookmark(url, tab?.title.orEmpty())
                    toast(if (added) "Добавлено в закладки" else "Удалено из закладок")
                }
                3 -> showEntries("Закладки", store.bookmarks().reversed(), onRemove = { store.removeBookmark(it.url) })
                4 -> showEntries("История", store.history(), onRemove = { store.removeHistory(it.url) }, onClear = { store.clearHistory() })
                5 -> startActivity(Intent(DownloadManager.ACTION_VIEW_DOWNLOADS))
                6 -> openFind()
                7 -> startActivity(Intent.createChooser(Intent(Intent.ACTION_SEND).apply {
                    type = "text/plain"; putExtra(Intent.EXTRA_TEXT, url); putExtra(Intent.EXTRA_SUBJECT, tab?.title)
                }, "Поделиться"))
                8 -> {
                    store.desktopMode = !store.desktopMode
                    tabs.forEach { it.web.settings.userAgentString = userAgent(WebSettings.getDefaultUserAgent(this)) }
                    tab?.web?.reload()
                }
                9 -> chooseEngine()
                10 -> clearData()
                11 -> { tabs.toList().forEach { closeTab(it) } }
            }
            true
        }
        menu.show()
    }

    private fun showTabs() {
        lateinit var dialog: AlertDialog
        val adapter = object : BaseAdapter() {
            override fun getCount() = tabs.size
            override fun getItem(position: Int) = tabs[position]
            override fun getItemId(position: Int) = position.toLong()
            override fun getView(position: Int, convertView: View?, parent: ViewGroup): View {
                val t = tabs[position]
                val row = LinearLayout(this@MainActivity).apply {
                    orientation = LinearLayout.HORIZONTAL
                    gravity = Gravity.CENTER_VERTICAL
                    setPadding(dp(20), dp(6), dp(6), dp(6))
                    if (t == current) setBackgroundColor(0x22E0A100)
                }
                val texts = LinearLayout(this@MainActivity).apply { orientation = LinearLayout.VERTICAL }
                texts.addView(TextView(this@MainActivity).apply { text = t.title; textSize = 15f; maxLines = 1; setTextColor(getColor(R.color.text)) })
                texts.addView(TextView(this@MainActivity).apply { text = displayUrl(t.url).ifEmpty { "Новая вкладка" }; textSize = 12f; maxLines = 1; setTextColor(getColor(R.color.muted)) })
                row.addView(texts, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
                row.addView(ImageButton(this@MainActivity).apply {
                    setImageResource(R.drawable.ic_close)
                    setBackgroundResource(R.drawable.ripple)
                    contentDescription = "Закрыть вкладку"
                    isFocusable = false
                    setOnClickListener {
                        closeTab(t)
                        if (tabs.size == 1 && displayUrl(tabs[0].url).isEmpty()) dialog.dismiss() else notifyDataSetChanged()
                    }
                }, LinearLayout.LayoutParams(dp(44), dp(44)))
                return row
            }
        }
        val list = ListView(this).apply { this.adapter = adapter }
        list.setOnItemClickListener { _, _, pos, _ -> switchTo(tabs[pos]); dialog.dismiss() }
        dialog = AlertDialog.Builder(this)
            .setTitle("Вкладки: ${tabs.size}")
            .setView(list)
            .setPositiveButton("Новая вкладка") { _, _ -> newTab(NEW_TAB); focusAddress() }
            .setNegativeButton("Закрыть", null)
            .create()
        dialog.show()
    }

    /** Список закладок или истории: нажатие — открыть, долгое нажатие — удалить. */
    private fun showEntries(title: String, entries: List<Store.Entry>, onRemove: (Store.Entry) -> Unit, onClear: (() -> Unit)? = null) {
        if (entries.isEmpty()) { toast("$title: пусто"); return }
        val items = entries.toMutableList()
        val adapter = object : ArrayAdapter<Store.Entry>(this, android.R.layout.simple_list_item_2, android.R.id.text1, items) {
            override fun getView(position: Int, convertView: View?, parent: ViewGroup): View {
                val v = super.getView(position, convertView, parent)
                val e = items[position]
                v.findViewById<TextView>(android.R.id.text1).apply { text = e.title; maxLines = 1 }
                v.findViewById<TextView>(android.R.id.text2).apply { text = e.url; maxLines = 1 }
                return v
            }
        }
        val list = ListView(this).apply { this.adapter = adapter }
        val builder = AlertDialog.Builder(this).setTitle(title).setView(list).setNegativeButton("Закрыть", null)
        if (onClear != null) builder.setNeutralButton("Очистить всё") { _, _ -> onClear(); toast("$title очищена") }
        val dialog = builder.create()
        list.setOnItemClickListener { _, _, pos, _ -> current?.web?.loadUrl(items[pos].url); dialog.dismiss() }
        list.setOnItemLongClickListener { _, _, pos, _ ->
            val e = items[pos]
            PopupMenu(this, list.getChildAt(pos - list.firstVisiblePosition)).apply {
                menu.add("Открыть в новой вкладке").setOnMenuItemClickListener { newTab(e.url); dialog.dismiss(); true }
                menu.add("Копировать адрес").setOnMenuItemClickListener { copy(e.url); true }
                menu.add("Удалить").setOnMenuItemClickListener { onRemove(e); items.removeAt(pos); adapter.notifyDataSetChanged(); true }
            }.show()
            true
        }
        dialog.show()
    }

    private fun chooseEngine() {
        val keys = Omnibox.ENGINES.keys.toList()
        AlertDialog.Builder(this)
            .setTitle("Поисковая система")
            .setSingleChoiceItems(keys.map { Omnibox.ENGINES.getValue(it).name }.toTypedArray(), keys.indexOf(store.searchEngine)) { d, i ->
                store.searchEngine = keys[i]
                d.dismiss()
                if (current?.url?.startsWith(NEW_TAB) == true) current?.web?.reload()
            }
            .show()
    }

    private fun clearData() {
        AlertDialog.Builder(this)
            .setTitle("Очистить данные?")
            .setMessage("Будут удалены история, cookie, кэш и данные сайтов. Вы выйдете из аккаунтов на сайтах.")
            .setPositiveButton("Очистить") { _, _ ->
                store.clearHistory()
                CookieManager.getInstance().removeAllCookies(null)
                WebStorage.getInstance().deleteAllData()
                tabs.forEach { it.web.clearCache(true); it.web.clearHistory() }
                updateUi()
                toast("Данные очищены")
            }
            .setNegativeButton("Отмена", null)
            .show()
    }

    private fun onLongPress(web: WebView): Boolean {
        val hit = web.hitTestResult
        val link = hit.extra ?: return false
        val isImage = hit.type == WebView.HitTestResult.IMAGE_TYPE || hit.type == WebView.HitTestResult.SRC_IMAGE_ANCHOR_TYPE
        val isLink = hit.type == WebView.HitTestResult.SRC_ANCHOR_TYPE || hit.type == WebView.HitTestResult.SRC_IMAGE_ANCHOR_TYPE
        if (!isImage && !isLink) return false
        val href = if (hit.type == WebView.HitTestResult.SRC_IMAGE_ANCHOR_TYPE) {
            // для картинки-ссылки hitTestResult отдаёт адрес картинки; адрес ссылки — через requestFocusNodeHref
            val msg = Message.obtain()
            web.requestFocusNodeHref(msg)
            msg.data.getString("url") ?: link
        } else link
        val options = mutableListOf<Pair<String, () -> Unit>>()
        if (isLink) {
            options += "Открыть в новой вкладке" to { newTab(href, activate = false, after = current); toast("Открыто в фоновой вкладке") }
            options += "Копировать адрес ссылки" to { copy(href) }
            options += "Поделиться ссылкой" to { startActivity(Intent.createChooser(Intent(Intent.ACTION_SEND).setType("text/plain").putExtra(Intent.EXTRA_TEXT, href), null)) }
        }
        if (isImage) {
            options += "Открыть изображение" to { newTab(link) }
            options += "Скачать изображение" to { download(link, web.settings.userAgentString, null, null) }
        }
        AlertDialog.Builder(this)
            .setTitle(href.take(120))
            .setItems(options.map { it.first }.toTypedArray()) { _, i -> options[i].second() }
            .show()
        return true
    }

    // ------------------------------------------------------------------ поиск по странице

    private fun setupFindBar() {
        findInput.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, a: Int, b: Int, c: Int) {}
            override fun onTextChanged(s: CharSequence?, a: Int, b: Int, c: Int) {}
            override fun afterTextChanged(s: Editable?) {
                if (s.isNullOrEmpty()) { current?.web?.clearMatches(); findCount.text = "" } else current?.web?.findAllAsync(s.toString())
            }
        })
        findInput.setOnEditorActionListener { _, _, _ -> current?.web?.findNext(true); true }
        findViewById<View>(R.id.findNext).setOnClickListener { current?.web?.findNext(true) }
        findViewById<View>(R.id.findPrev).setOnClickListener { current?.web?.findNext(false) }
        findViewById<View>(R.id.findClose).setOnClickListener { closeFind() }
    }

    private fun openFind() {
        findBar.visibility = View.VISIBLE
        findInput.requestFocus()
        (getSystemService(Context.INPUT_METHOD_SERVICE) as InputMethodManager).showSoftInput(findInput, 0)
    }

    private fun closeFind() {
        if (findBar.visibility != View.VISIBLE) return
        findBar.visibility = View.GONE
        findInput.setText("")
        current?.web?.clearMatches()
        (getSystemService(Context.INPUT_METHOD_SERVICE) as InputMethodManager).hideSoftInputFromWindow(findInput.windowToken, 0)
    }

    // ------------------------------------------------------------------ загрузки

    private fun download(url: String, userAgent: String?, disposition: String?, mime: String?) {
        if (url.startsWith("blob:") || url.startsWith("data:")) { toast("Этот тип загрузки пока не поддерживается"); return }
        val run = {
            val name = URLUtil.guessFileName(url, disposition, mime)
            runCatching {
                val req = DownloadManager.Request(Uri.parse(url))
                    .setTitle(name)
                    .setMimeType(mime)
                    .addRequestHeader("User-Agent", userAgent ?: "")
                    .setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED)
                    .setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, name)
                CookieManager.getInstance().getCookie(url)?.let { req.addRequestHeader("Cookie", it) }
                (getSystemService(Context.DOWNLOAD_SERVICE) as DownloadManager).enqueue(req)
                toast("Загрузка: $name")
            }.onFailure { toast("Не удалось скачать: ${it.message}") }
            Unit
        }
        if (Build.VERSION.SDK_INT <= Build.VERSION_CODES.P &&
            checkSelfPermission(Manifest.permission.WRITE_EXTERNAL_STORAGE) != PackageManager.PERMISSION_GRANTED
        ) {
            pendingDownload = run
            requestPermissions(arrayOf(Manifest.permission.WRITE_EXTERNAL_STORAGE), REQ_STORAGE)
        } else run()
    }

    // ------------------------------------------------------------------ разрешения и выбор файлов

    private fun withPermissions(perms: Array<String>, then: (Boolean) -> Unit) {
        val missing = perms.filter { checkSelfPermission(it) != PackageManager.PERMISSION_GRANTED }
        if (missing.isEmpty()) return then(true)
        pendingPermission = then
        requestPermissions(missing.toTypedArray(), REQ_PERMS)
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, results: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, results)
        val ok = results.isNotEmpty() && results.all { it == PackageManager.PERMISSION_GRANTED }
        when (requestCode) {
            REQ_PERMS -> { pendingPermission?.invoke(ok); pendingPermission = null }
            REQ_STORAGE -> { if (ok) pendingDownload?.invoke() else toast("Нет доступа к памяти"); pendingDownload = null }
        }
    }

    @Deprecated("Deprecated in Java")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        @Suppress("DEPRECATION")
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == REQ_FILE) {
            fileCallback?.onReceiveValue(WebChromeClient.FileChooserParams.parseResult(resultCode, data))
            fileCallback = null
        }
    }

    private fun askSite(origin: String, what: String, then: (Boolean) -> Unit) {
        AlertDialog.Builder(this)
            .setMessage("$origin запрашивает доступ: $what")
            .setPositiveButton("Разрешить") { _, _ -> then(true) }
            .setNegativeButton("Запретить") { _, _ -> then(false) }
            .setOnCancelListener { then(false) }
            .show()
    }

    // ------------------------------------------------------------------ WebView

    private fun tabOf(view: WebView?) = tabs.find { it.web == view }

    private inner class Client : WebViewClient() {
        override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
            val uri = request.url
            return when (uri.scheme?.lowercase()) {
                "http", "https", "about", "data", "file" -> false
                "pitbrowser" -> { uri.getQueryParameter("q")?.let { q -> Omnibox.toUrl(q, store.searchEngine)?.let { view.loadUrl(it) } }; true }
                "intent" -> {
                    runCatching {
                        val intent = Intent.parseUri(uri.toString(), Intent.URI_INTENT_SCHEME)
                        intent.addCategory(Intent.CATEGORY_BROWSABLE).setComponent(null).setSelector(null)
                        try { startActivity(intent) } catch (e: ActivityNotFoundException) {
                            intent.getStringExtra("browser_fallback_url")?.let { view.loadUrl(it) }
                                ?: intent.`package`?.let { view.loadUrl("https://play.google.com/store/apps/details?id=$it") }
                        }
                    }
                    true
                }
                else -> { // tel:, mailto:, tg:, market: и т.п. — во внешнее приложение
                    try { startActivity(Intent(Intent.ACTION_VIEW, uri).addCategory(Intent.CATEGORY_BROWSABLE)) } catch (e: ActivityNotFoundException) { toast("Нет приложения для ${uri.scheme}:") }
                    true
                }
            }
        }

        override fun onPageStarted(view: WebView, url: String, favicon: Bitmap?) {
            if (view == current?.web) { progress.visibility = View.VISIBLE; updateUi() }
        }

        override fun onPageFinished(view: WebView, url: String) {
            val tab = tabOf(view) ?: return
            if (url.startsWith(NEW_TAB)) {
                tab.title = "Новая вкладка"
                view.evaluateJavascript("render(${newTabData()})", null)
            } else if (url.startsWith("http")) {
                tab.title = view.title?.takeIf { it.isNotBlank() } ?: url
                store.addHistory(url, tab.title)
            }
            if (view == current?.web) { progress.visibility = View.INVISIBLE; updateUi() }
        }

        override fun doUpdateVisitedHistory(view: WebView, url: String, isReload: Boolean) {
            if (view == current?.web) updateUi()
        }

        override fun onRenderProcessGone(view: WebView, detail: android.webkit.RenderProcessGoneDetail): Boolean {
            // упал процесс страницы — пересоздаём вкладку вместо падения приложения
            val tab = tabOf(view) ?: return true
            val url = tab.url
            val i = tabs.indexOf(tab)
            val wasCurrent = tab == current
            if (wasCurrent) { container.removeView(view); current = null }
            tabs.removeAt(i)
            view.destroy()
            val fresh = Tab(createWebView())
            tabs.add(i, fresh)
            fresh.web.loadUrl(url.ifEmpty { NEW_TAB })
            if (wasCurrent) switchTo(fresh)
            toast("Страница перезагружена после сбоя")
            return true
        }
    }

    private fun newTabData(): String {
        val tiles = store.bookmarks().takeLast(12).map { it.url to it.title }.ifEmpty { DEFAULT_TILES }
        val arr = JSONArray()
        tiles.forEach { (url, title) -> arr.put(JSONObject().put("url", url).put("title", title)) }
        return JSONObject()
            .put("engine", Omnibox.ENGINES[store.searchEngine]?.name ?: "Google")
            .put("tiles", arr)
            .toString()
    }

    private inner class Chrome : WebChromeClient() {
        override fun onProgressChanged(view: WebView, newProgress: Int) {
            if (view != current?.web) return
            progress.progress = newProgress
            progress.visibility = if (newProgress in 1..99) View.VISIBLE else View.INVISIBLE
        }

        override fun onReceivedTitle(view: WebView, title: String?) {
            val tab = tabOf(view) ?: return
            if (!title.isNullOrBlank() && !tab.url.startsWith(NEW_TAB)) {
                tab.title = title
                store.updateHistoryTitle(tab.url, title)
            }
        }

        // target="_blank" и window.open → новая вкладка
        override fun onCreateWindow(view: WebView, isDialog: Boolean, isUserGesture: Boolean, resultMsg: Message): Boolean {
            if (!isUserGesture) return false // блокировка всплывающих окон без нажатия пользователя
            val tab = newTab("", after = tabOf(view))
            (resultMsg.obj as WebView.WebViewTransport).webView = tab.web
            resultMsg.sendToTarget()
            return true
        }

        override fun onCloseWindow(window: WebView) {
            tabOf(window)?.let { closeTab(it) }
        }

        override fun onShowFileChooser(view: WebView, callback: ValueCallback<Array<Uri>>, params: FileChooserParams): Boolean {
            fileCallback?.onReceiveValue(null)
            fileCallback = callback
            return try {
                @Suppress("DEPRECATION")
                startActivityForResult(params.createIntent(), REQ_FILE)
                true
            } catch (e: ActivityNotFoundException) {
                fileCallback = null
                false
            }
        }

        override fun onGeolocationPermissionsShowPrompt(origin: String, callback: GeolocationPermissions.Callback) {
            askSite(origin, "местоположение") { allow ->
                if (!allow) return@askSite callback.invoke(origin, false, false)
                withPermissions(arrayOf(Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION)) { ok ->
                    callback.invoke(origin, ok, false)
                }
            }
        }

        override fun onPermissionRequest(request: PermissionRequest) {
            val res = request.resources
            val perms = mutableListOf<String>()
            val names = mutableListOf<String>()
            if (PermissionRequest.RESOURCE_VIDEO_CAPTURE in res) { perms += Manifest.permission.CAMERA; names += "камера" }
            if (PermissionRequest.RESOURCE_AUDIO_CAPTURE in res) { perms += Manifest.permission.RECORD_AUDIO; names += "микрофон" }
            if (perms.isEmpty()) return request.deny()
            askSite(request.origin.toString(), names.joinToString(", ")) { allow ->
                if (!allow) return@askSite request.deny()
                withPermissions(perms.toTypedArray()) { ok -> if (ok) request.grant(res) else request.deny() }
            }
        }

        // полноэкранное видео
        override fun onShowCustomView(view: View, callback: CustomViewCallback) {
            if (fullscreenView != null) { callback.onCustomViewHidden(); return }
            fullscreenView = view
            fullscreenCallback = callback
            (window.decorView as FrameLayout).addView(view, FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT))
            setSystemBarsHidden(true)
        }

        override fun onHideCustomView() {
            val v = fullscreenView ?: return
            (window.decorView as FrameLayout).removeView(v)
            fullscreenView = null
            fullscreenCallback = null
            setSystemBarsHidden(false)
        }
    }

    private fun setSystemBarsHidden(hidden: Boolean) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            val c = window.insetsController ?: return
            if (hidden) {
                c.hide(WindowInsets.Type.systemBars())
                c.systemBarsBehavior = WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
            } else c.show(WindowInsets.Type.systemBars())
        } else {
            @Suppress("DEPRECATION")
            window.decorView.systemUiVisibility = if (hidden)
                View.SYSTEM_UI_FLAG_FULLSCREEN or View.SYSTEM_UI_FLAG_HIDE_NAVIGATION or View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
            else 0
        }
    }

    // ------------------------------------------------------------------ мелочи

    private fun copy(text: String) {
        (getSystemService(Context.CLIPBOARD_SERVICE) as android.content.ClipboardManager)
            .setPrimaryClip(android.content.ClipData.newPlainText("url", text))
        toast("Скопировано")
    }

    private fun toast(s: String) = Toast.makeText(this, s, Toast.LENGTH_SHORT).show()
    private fun dp(v: Int) = (v * resources.displayMetrics.density).toInt()

    companion object {
        const val NEW_TAB = "file:///android_asset/newtab.html"
        private const val REQ_FILE = 1
        private const val REQ_PERMS = 2
        private const val REQ_STORAGE = 3
        private val DEFAULT_TILES = listOf(
            "https://www.youtube.com/" to "YouTube",
            "https://ru.wikipedia.org/" to "Wikipedia",
            "https://github.com/" to "GitHub",
            "https://web.telegram.org/" to "Telegram",
            "https://www.robutpit.com/" to "Портфолио",
        )
    }
}
