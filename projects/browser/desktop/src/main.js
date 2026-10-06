'use strict';
// PitBrowser — главный процесс Electron.
// Каждое окно = BrowserWindow с панелью (src/ui) + по WebContentsView на вкладку.

const {
  app, BrowserWindow, WebContentsView, ipcMain, Menu, session,
  protocol, net, shell, clipboard, dialog, nativeTheme,
} = require('electron');
const path = require('path');
const fs = require('fs');
const { pathToFileURL } = require('url');
const { toUrl, SEARCH_ENGINES } = require('./omnibox');
const Store = require('./store');

const INTERNAL = 'pit';
const NEW_TAB = 'pit://newtab';
const PAGES_DIR = path.join(__dirname, 'pages');

protocol.registerSchemesAsPrivileged([
  { scheme: INTERNAL, privileges: { standard: true, secure: true, supportFetchAPI: true } },
]);

let store;
const windows = new Set();
const downloads = []; // {id, name, path, url, received, total, state}
let downloadSeq = 0;
let privateSeq = 0;

const isInternal = (url) => typeof url === 'string' && url.startsWith(INTERNAL + '://');

// Что показать в адресной строке: пусто для новой вкладки, исходный адрес для страницы ошибки.
function displayUrl(url) {
  if (url.startsWith(NEW_TAB)) return '';
  if (url.startsWith(INTERNAL + '://error')) {
    try { return new URL(url).searchParams.get('url') || url; } catch { return url; }
  }
  return url;
}

// ---------------------------------------------------------------- окно

class BrowserWin {
  constructor({ privateMode = false, url } = {}) {
    this.privateMode = privateMode;
    this.partition = privateMode ? `pit-private-${++privateSeq}` : 'persist:pit';
    this.tabs = [];          // {id, view, title, url, favicon, loading}
    this.activeId = null;
    this.chromeHeight = 84;
    this.closedTabs = [];
    this.tabSeq = 0;

    this.win = new BrowserWindow({
      width: 1280,
      height: 820,
      minWidth: 420,
      minHeight: 300,
      title: privateMode ? 'PitBrowser — приватное окно' : 'PitBrowser',
      icon: path.join(__dirname, '..', 'build', 'icon.png'),
      backgroundColor: privateMode ? '#1b1530' : (nativeTheme.shouldUseDarkColors ? '#1e1f24' : '#f1f3f6'),
      autoHideMenuBar: true,
      webPreferences: {
        preload: path.join(__dirname, 'ui-preload.js'),
        contextIsolation: true,
        sandbox: true,
      },
    });
    this.win.loadFile(path.join(__dirname, 'ui', 'index.html'), {
      query: { private: privateMode ? '1' : '0' },
    });
    this.win.on('resize', () => this.layout());
    this.win.on('enter-full-screen', () => this.layout());
    this.win.on('leave-full-screen', () => this.layout());
    this.win.on('closed', () => {
      windows.delete(this);
      if (privateMode) session.fromPartition(this.partition).clearStorageData().catch(() => {});
    });
    this.win.webContents.once('did-finish-load', () => this.newTab(url || NEW_TAB));
    if (privateMode) setupSession(session.fromPartition(this.partition), true);
    windows.add(this);
  }

  get ui() { return this.win.webContents; }
  tab(id) { return this.tabs.find((t) => t.id === id); }
  get active() { return this.tab(this.activeId); }

  newTab(url = NEW_TAB, { background = false, index } = {}) {
    const view = new WebContentsView({
      webPreferences: {
        partition: this.partition,
        preload: path.join(__dirname, 'page-preload.js'),
        contextIsolation: true,
        sandbox: true,
      },
    });
    const t = { id: ++this.tabSeq, view, title: 'Новая вкладка', url, favicon: null, loading: true };
    if (index === undefined) this.tabs.push(t); else this.tabs.splice(index, 0, t);
    this.wireTab(t);
    view.webContents.loadURL(url).catch(() => {});
    if (!background || this.tabs.length === 1) this.activate(t.id); else this.sendTabs();
    return t;
  }

  wireTab(t) {
    const wc = t.view.webContents;
    const update = () => {
      t.url = wc.getURL() || t.url;
      t.title = wc.getTitle() || t.url;
      this.sendTabs();
    };
    wc.on('page-title-updated', update);
    wc.on('did-navigate', update);
    wc.on('did-navigate-in-page', update);
    wc.on('did-start-loading', () => { t.loading = true; this.sendTabs(); });
    wc.on('did-stop-loading', () => {
      t.loading = false;
      update();
      if (!this.privateMode && !isInternal(t.url) && /^https?:/.test(t.url)) {
        store.addHistory({ url: t.url, title: t.title, favicon: t.favicon });
      }
    });
    wc.on('page-favicon-updated', (_e, icons) => { t.favicon = icons[0] || null; this.sendTabs(); });
    wc.on('did-fail-load', (_e, code, desc, url, isMain) => {
      if (!isMain || code === -3) return; // -3 = отменено пользователем
      wc.loadURL(`${INTERNAL}://error?code=${code}&desc=${encodeURIComponent(desc)}&url=${encodeURIComponent(url)}`);
    });
    wc.on('found-in-page', (_e, r) => this.ui.send('find:result', { active: r.activeMatchOrdinal, total: r.matches }));
    wc.on('enter-html-full-screen', () => { this.htmlFullscreen = true; this.layout(); });
    wc.on('leave-html-full-screen', () => { this.htmlFullscreen = false; this.layout(); });
    wc.setWindowOpenHandler(({ url, disposition }) => {
      if (disposition === 'new-window' && !url) return { action: 'allow' };
      this.newTab(url, { background: disposition === 'background-tab', index: this.tabs.indexOf(t) + 1 });
      return { action: 'deny' };
    });
    wc.on('will-navigate', (e, url) => {
      if (/^(mailto|tel|magnet|tg|whatsapp):/i.test(url)) { e.preventDefault(); shell.openExternal(url); }
    });
    wc.on('context-menu', (_e, p) => this.contextMenu(t, p));
    wc.on('zoom-changed', (_e, dir) => this.zoom(dir === 'in' ? 0.5 : -0.5));
  }

  activate(id) {
    const t = this.tab(id);
    if (!t) return;
    const prev = this.active;
    if (prev && prev !== t) this.win.contentView.removeChildView(prev.view);
    this.activeId = id;
    this.win.contentView.addChildView(t.view);
    this.layout();
    t.view.webContents.focus();
    this.sendTabs();
  }

  closeTab(id) {
    const i = this.tabs.findIndex((t) => t.id === id);
    if (i < 0) return;
    const [t] = this.tabs.splice(i, 1);
    if (t.url !== NEW_TAB) this.closedTabs.push(t.url);
    this.win.contentView.removeChildView(t.view);
    t.view.webContents.close();
    if (!this.tabs.length) { this.win.close(); return; }
    if (this.activeId === id) this.activate(this.tabs[Math.min(i, this.tabs.length - 1)].id);
    else this.sendTabs();
  }

  reopenClosed() {
    const url = this.closedTabs.pop();
    if (url) this.newTab(url);
  }

  cycle(delta) {
    if (this.tabs.length < 2) return;
    const i = this.tabs.findIndex((t) => t.id === this.activeId);
    this.activate(this.tabs[(i + delta + this.tabs.length) % this.tabs.length].id);
  }

  moveTab(id, toIndex) {
    const i = this.tabs.findIndex((t) => t.id === id);
    if (i < 0) return;
    const [t] = this.tabs.splice(i, 1);
    this.tabs.splice(Math.max(0, Math.min(toIndex, this.tabs.length)), 0, t);
    this.sendTabs();
  }

  layout() {
    const t = this.active;
    if (!t) return;
    const [w, h] = this.win.getContentSize();
    const top = this.htmlFullscreen ? 0 : this.chromeHeight;
    t.view.setBounds({ x: 0, y: top, width: w, height: Math.max(0, h - top) });
  }

  navigate(input) {
    const url = toUrl(input, store.get('settings').searchEngine);
    if (!url) return;
    const t = this.active || this.newTab(url);
    t.view.webContents.loadURL(url).catch(() => {});
    t.view.webContents.focus();
  }

  zoom(step) {
    const wc = this.active?.view.webContents;
    if (!wc) return;
    const level = step === 0 ? 0 : Math.max(-8, Math.min(9, wc.getZoomLevel() + step));
    wc.setZoomLevel(level);
    this.ui.send('zoom', Math.round(Math.pow(1.2, level) * 100));
  }

  tabState(t) {
    const wc = t.view.webContents;
    return {
      id: t.id,
      title: t.title,
      url: displayUrl(t.url),
      favicon: t.favicon,
      loading: t.loading,
      canBack: wc.navigationHistory.canGoBack(),
      canForward: wc.navigationHistory.canGoForward(),
      bookmarked: store.isBookmarked(t.url),
      secure: t.url.startsWith('https://') || (isInternal(t.url) && !t.url.startsWith(INTERNAL + '://error')),
    };
  }

  sendTabs() {
    if (this.ui.isDestroyed()) return;
    this.ui.send('tabs', { tabs: this.tabs.map((t) => this.tabState(t)), activeId: this.activeId });
    const a = this.active;
    if (a) this.win.setTitle(`${a.title} — PitBrowser${this.privateMode ? ' (приватно)' : ''}`);
  }

  contextMenu(t, p) {
    const wc = t.view.webContents;
    const items = [];
    if (p.linkURL) {
      items.push(
        { label: 'Открыть ссылку в новой вкладке', click: () => this.newTab(p.linkURL, { background: true, index: this.tabs.indexOf(t) + 1 }) },
        { label: 'Открыть ссылку в приватном окне', click: () => new BrowserWin({ privateMode: true, url: p.linkURL }) },
        { label: 'Копировать адрес ссылки', click: () => clipboard.writeText(p.linkURL) },
        { type: 'separator' },
      );
    }
    if (p.mediaType === 'image' && p.srcURL) {
      items.push(
        { label: 'Открыть изображение в новой вкладке', click: () => this.newTab(p.srcURL) },
        { label: 'Сохранить изображение…', click: () => wc.downloadURL(p.srcURL) },
        { label: 'Копировать изображение', click: () => wc.copyImageAt(p.x, p.y) },
        { type: 'separator' },
      );
    }
    if (p.selectionText) {
      const q = p.selectionText.trim().slice(0, 200);
      items.push(
        { label: 'Копировать', role: 'copy' },
        { label: `Искать «${q.length > 30 ? q.slice(0, 30) + '…' : q}»`, click: () => this.newTab(toUrl(q, store.get('settings').searchEngine, true)) },
        { type: 'separator' },
      );
    }
    if (p.isEditable) {
      items.push(
        { label: 'Отменить', role: 'undo' }, { label: 'Повторить', role: 'redo' }, { type: 'separator' },
        { label: 'Вырезать', role: 'cut' }, { label: 'Копировать', role: 'copy' },
        { label: 'Вставить', role: 'paste' }, { label: 'Выделить всё', role: 'selectAll' },
        { type: 'separator' },
      );
    }
    if (!p.linkURL && !p.selectionText && !p.isEditable && p.mediaType === 'none') {
      items.push(
        { label: 'Назад', enabled: wc.navigationHistory.canGoBack(), click: () => wc.navigationHistory.goBack() },
        { label: 'Вперёд', enabled: wc.navigationHistory.canGoForward(), click: () => wc.navigationHistory.goForward() },
        { label: 'Обновить', click: () => wc.reload() },
        { type: 'separator' },
        { label: 'Сохранить страницу как…', click: () => savePage(this.win, wc) },
        { label: 'Печать…', click: () => wc.print() },
        { type: 'separator' },
      );
    }
    items.push({ label: 'Просмотреть код элемента', click: () => wc.inspectElement(p.x, p.y) });
    Menu.buildFromTemplate(items).popup({ window: this.win });
  }
}

async function savePage(win, wc) {
  const name = (wc.getTitle() || 'page').replace(/[\\/:*?"<>|]+/g, '_').slice(0, 100);
  const { canceled, filePath } = await dialog.showSaveDialog(win, {
    defaultPath: path.join(app.getPath('downloads'), name + '.html'),
    filters: [{ name: 'Веб-страница целиком', extensions: ['html'] }],
  });
  if (!canceled && filePath) wc.savePage(filePath, 'HTMLComplete').catch(() => {});
}

// ---------------------------------------------------------------- окна и вкладки

function winFromSender(sender) {
  for (const w of windows) {
    if (w.ui === sender) return w;
    if (w.tabs.some((t) => t.view.webContents === sender)) return w;
  }
  return null;
}

function focusedWin() {
  const bw = BrowserWindow.getFocusedWindow();
  for (const w of windows) if (w.win === bw) return w;
  return [...windows].pop() || null;
}

function broadcast(channel, payload) {
  for (const w of windows) {
    if (!w.ui.isDestroyed()) w.ui.send(channel, payload);
    for (const t of w.tabs) if (isInternal(t.url)) t.view.webContents.send(channel, payload);
  }
}

// ---------------------------------------------------------------- сессия: загрузки, разрешения

function setupSession(ses, privateMode = false) {
  ses.setUserAgent(ses.getUserAgent().replace(/\s?Electron\/\S+/, '').replace(/\s?pitbrowser\/\S+/i, ''));
  ses.protocol.handle(INTERNAL, serveInternal);

  ses.on('will-download', (_e, item) => {
    const dir = store.get('settings').downloadDir || app.getPath('downloads');
    item.setSavePath(uniquePath(path.join(dir, item.getFilename())));
    const d = {
      id: ++downloadSeq, name: path.basename(item.getSavePath()), path: item.getSavePath(),
      url: item.getURL(), received: 0, total: item.getTotalBytes(), state: 'progressing',
    };
    downloads.unshift(d);
    d.cancel = () => item.cancel();
    const push = () => broadcast('downloads', publicDownloads());
    item.on('updated', (_ev, state) => { d.received = item.getReceivedBytes(); d.total = item.getTotalBytes(); d.state = state === 'interrupted' ? 'interrupted' : 'progressing'; push(); });
    item.once('done', (_ev, state) => { d.received = item.getReceivedBytes(); d.state = state; push(); });
    push();
  });

  // Камера/микрофон/геолокация/уведомления — спрашиваем пользователя.
  const ask = new Set(['media', 'geolocation', 'notifications', 'midi', 'clipboard-read', 'display-capture']);
  const allowAlways = new Set(['fullscreen', 'clipboard-sanitized-write', 'pointerLock']);
  const decided = new Map(); // `${origin}|${perm}` -> bool (на время сеанса)
  ses.setPermissionRequestHandler((wc, permission, callback, details) => {
    if (allowAlways.has(permission)) return callback(true);
    if (!ask.has(permission)) return callback(false);
    let origin;
    try { origin = new URL(details.requestingUrl).origin; } catch { return callback(false); }
    const key = `${origin}|${permission}`;
    if (decided.has(key)) return callback(decided.get(key));
    const names = { media: 'камеру/микрофон', geolocation: 'местоположение', notifications: 'уведомления', midi: 'MIDI-устройства', 'clipboard-read': 'буфер обмена', 'display-capture': 'запись экрана' };
    const bw = BrowserWindow.fromWebContents(wc.hostWebContents || wc) || BrowserWindow.getFocusedWindow();
    dialog.showMessageBox(bw, {
      type: 'question',
      buttons: ['Разрешить', 'Запретить'],
      defaultId: 1,
      cancelId: 1,
      message: `${origin} запрашивает доступ: ${names[permission] || permission}`,
    }).then(({ response }) => {
      const ok = response === 0;
      if (!privateMode) decided.set(key, ok);
      callback(ok);
    });
  });
}

function uniquePath(p) {
  if (!fs.existsSync(p)) return p;
  const { dir, name, ext } = path.parse(p);
  for (let i = 1; ; i++) {
    const c = path.join(dir, `${name} (${i})${ext}`);
    if (!fs.existsSync(c)) return c;
  }
}

const publicDownloads = () => downloads.map(({ cancel, ...d }) => d);

// pit://newtab, pit://history ... → файлы из src/pages
async function serveInternal(req) {
  const { host, pathname } = new URL(req.url);
  const page = host === 'newtab' || host === 'history' || host === 'bookmarks' || host === 'downloads'
    || host === 'settings' || host === 'error' ? host : null;
  let file;
  if (pathname && pathname !== '/') file = path.join(PAGES_DIR, path.normalize(pathname).replace(/^([/\\])+/, ''));
  else if (page) file = path.join(PAGES_DIR, page + '.html');
  if (!file || !file.startsWith(PAGES_DIR)) return new Response('Not found', { status: 404 });
  return net.fetch(pathToFileURL(file).toString());
}

// ---------------------------------------------------------------- IPC

function fromInternalPage(e) {
  return isInternal(e.senderFrame?.url) || e.sender.getURL().startsWith('file://');
}

function registerIpc() {
  const on = (ch, fn) => ipcMain.on(ch, (e, ...a) => { const w = winFromSender(e.sender); if (w) fn(w, ...a); });

  on('tab:new', (w, url) => w.newTab(url || NEW_TAB));
  on('tab:close', (w, id) => w.closeTab(id ?? w.activeId));
  on('tab:activate', (w, id) => w.activate(id));
  on('tab:move', (w, id, index) => w.moveTab(id, index));
  on('nav:go', (w, input) => w.navigate(input));
  on('nav:back', (w) => w.active?.view.webContents.navigationHistory.goBack());
  on('nav:forward', (w) => w.active?.view.webContents.navigationHistory.goForward());
  on('nav:reload', (w, hard) => { const wc = w.active?.view.webContents; if (wc) hard ? wc.reloadIgnoringCache() : wc.reload(); });
  on('nav:stop', (w) => w.active?.view.webContents.stop());
  on('nav:home', (w) => w.active?.view.webContents.loadURL(store.get('settings').homePage || NEW_TAB));
  on('ui:chromeHeight', (w, h) => { w.chromeHeight = Math.max(0, Math.round(h)); w.layout(); });
  on('ui:focusPage', (w) => w.active?.view.webContents.focus());
  on('find', (w, text, opts) => { const wc = w.active?.view.webContents; if (wc && text) wc.findInPage(text, opts || {}); });
  on('find:stop', (w) => w.active?.view.webContents.stopFindInPage('clearSelection'));
  on('zoom', (w, step) => w.zoom(step));
  on('window:private', () => new BrowserWin({ privateMode: true }));
  on('window:new', () => new BrowserWin());
  on('bookmark:toggle', (w) => {
    const t = w.active;
    if (!t || isInternal(t.url)) return;
    store.toggleBookmark({ url: t.url, title: t.title, favicon: t.favicon });
    broadcast('bookmarks', store.get('bookmarks'));
    for (const x of windows) x.sendTabs();
  });

  // Данные для внутренних страниц и панели закладок.
  const handle = (ch, fn) => ipcMain.handle(ch, (e, ...a) => {
    if (!fromInternalPage(e)) throw new Error('forbidden');
    return fn(e, ...a);
  });
  handle('data:bookmarks', () => store.get('bookmarks'));
  handle('data:history', (_e, q) => store.searchHistory(q));
  handle('data:downloads', () => publicDownloads());
  handle('data:settings', () => ({ ...store.get('settings'), engines: SEARCH_ENGINES }));
  handle('data:suggest', (_e, q) => store.suggest(q));
  handle('bookmarks:remove', (_e, url) => { store.removeBookmark(url); broadcast('bookmarks', store.get('bookmarks')); for (const x of windows) x.sendTabs(); return true; });
  handle('bookmarks:add', (_e, b) => {
    if (!b || !/^https?:\/\//.test(b.url)) return false;
    if (!store.isBookmarked(b.url)) store.toggleBookmark({ url: b.url, title: b.title || b.url });
    broadcast('bookmarks', store.get('bookmarks'));
    return true;
  });
  handle('history:remove', (_e, url) => { store.removeHistory(url); return true; });
  handle('history:clear', () => { store.clearHistory(); return true; });
  handle('downloads:open', (_e, id) => { const d = downloads.find((x) => x.id === id); if (d) shell.openPath(d.path); });
  handle('downloads:show', (_e, id) => { const d = downloads.find((x) => x.id === id); if (d) shell.showItemInFolder(d.path); });
  handle('downloads:cancel', (_e, id) => { downloads.find((x) => x.id === id)?.cancel?.(); });
  handle('downloads:clear', () => { for (let i = downloads.length - 1; i >= 0; i--) if (downloads[i].state !== 'progressing') downloads.splice(i, 1); broadcast('downloads', publicDownloads()); });
  handle('settings:set', (_e, patch) => {
    const allowed = ['searchEngine', 'homePage', 'showBookmarksBar', 'theme', 'downloadDir'];
    const s = store.get('settings');
    for (const k of allowed) if (patch && k in patch) s[k] = patch[k];
    store.set('settings', s);
    nativeTheme.themeSource = s.theme || 'system';
    broadcast('settings', s);
    return s;
  });
  handle('settings:pickDownloadDir', async (e) => {
    const r = await dialog.showOpenDialog(BrowserWindow.fromWebContents(e.sender) || undefined, { properties: ['openDirectory', 'createDirectory'] });
    return r.canceled ? null : r.filePaths[0];
  });
  handle('data:clearBrowsing', async () => {
    store.clearHistory();
    await session.fromPartition('persist:pit').clearStorageData();
    await session.fromPartition('persist:pit').clearCache();
    return true;
  });
  handle('nav:open', (e, url, newTab) => {
    const w = winFromSender(e.sender);
    if (!w || typeof url !== 'string') return;
    const target = toUrl(url, store.get('settings').searchEngine);
    if (!target) return;
    if (newTab) w.newTab(target, { background: true });
    else { const t = w.tabs.find((x) => x.view.webContents === e.sender) || w.active; t?.view.webContents.loadURL(target); }
  });
}

// ---------------------------------------------------------------- меню и горячие клавиши

function buildMenu() {
  const W = (fn) => () => { const w = focusedWin(); if (w) fn(w); };
  const isMac = process.platform === 'darwin';
  const template = [
    ...(isMac ? [{ role: 'appMenu' }] : []),
    {
      label: 'Файл',
      submenu: [
        { label: 'Новая вкладка', accelerator: 'CmdOrCtrl+T', click: W((w) => w.newTab()) },
        { label: 'Новое окно', accelerator: 'CmdOrCtrl+N', click: () => new BrowserWin() },
        { label: 'Приватное окно', accelerator: 'CmdOrCtrl+Shift+N', click: () => new BrowserWin({ privateMode: true }) },
        { label: 'Открыть закрытую вкладку', accelerator: 'CmdOrCtrl+Shift+T', click: W((w) => w.reopenClosed()) },
        { label: 'Закрыть вкладку', accelerator: 'CmdOrCtrl+W', click: W((w) => w.closeTab(w.activeId)) },
        { label: 'Сохранить страницу', accelerator: 'CmdOrCtrl+S', click: W((w) => w.active && savePage(w.win, w.active.view.webContents)) },
        { label: 'Печать', accelerator: 'CmdOrCtrl+P', click: W((w) => w.active?.view.webContents.print()) },
        { type: 'separator' },
        isMac ? { role: 'close' } : { role: 'quit', label: 'Выход' },
      ],
    },
    {
      label: 'Правка',
      submenu: [
        { role: 'undo', label: 'Отменить' }, { role: 'redo', label: 'Повторить' }, { type: 'separator' },
        { role: 'cut', label: 'Вырезать' }, { role: 'copy', label: 'Копировать' },
        { role: 'paste', label: 'Вставить' }, { role: 'selectAll', label: 'Выделить всё' },
        { type: 'separator' },
        { label: 'Найти на странице', accelerator: 'CmdOrCtrl+F', click: W((w) => w.ui.send('find:open')) },
      ],
    },
    {
      label: 'Вид',
      submenu: [
        { label: 'Адресная строка', accelerator: 'CmdOrCtrl+L', click: W((w) => w.ui.send('focus:address')) },
        { label: 'Адресная строка', accelerator: 'Alt+D', visible: false, click: W((w) => w.ui.send('focus:address')) },
        { label: 'Обновить', accelerator: 'CmdOrCtrl+R', click: W((w) => w.active?.view.webContents.reload()) },
        { label: 'Обновить', accelerator: 'F5', visible: false, click: W((w) => w.active?.view.webContents.reload()) },
        { label: 'Обновить без кэша', accelerator: 'CmdOrCtrl+Shift+R', click: W((w) => w.active?.view.webContents.reloadIgnoringCache()) },
        { label: 'Назад', accelerator: isMac ? 'Cmd+[' : 'Alt+Left', click: W((w) => w.active?.view.webContents.navigationHistory.goBack()) },
        { label: 'Вперёд', accelerator: isMac ? 'Cmd+]' : 'Alt+Right', click: W((w) => w.active?.view.webContents.navigationHistory.goForward()) },
        { type: 'separator' },
        { label: 'Увеличить', accelerator: 'CmdOrCtrl+=', click: W((w) => w.zoom(0.5)) },
        { label: 'Увеличить', accelerator: 'CmdOrCtrl+Plus', visible: false, click: W((w) => w.zoom(0.5)) },
        { label: 'Уменьшить', accelerator: 'CmdOrCtrl+-', click: W((w) => w.zoom(-0.5)) },
        { label: 'Сбросить масштаб', accelerator: 'CmdOrCtrl+0', click: W((w) => w.zoom(0)) },
        { type: 'separator' },
        { label: 'Следующая вкладка', accelerator: 'Ctrl+Tab', click: W((w) => w.cycle(1)) },
        { label: 'Предыдущая вкладка', accelerator: 'Ctrl+Shift+Tab', click: W((w) => w.cycle(-1)) },
        ...[1, 2, 3, 4, 5, 6, 7, 8].map((n) => ({
          label: `Вкладка ${n}`, accelerator: `CmdOrCtrl+${n}`, visible: false,
          click: W((w) => w.tabs[n - 1] && w.activate(w.tabs[n - 1].id)),
        })),
        { label: 'Последняя вкладка', accelerator: 'CmdOrCtrl+9', visible: false, click: W((w) => w.tabs.length && w.activate(w.tabs[w.tabs.length - 1].id)) },
        { type: 'separator' },
        { role: 'togglefullscreen', label: 'Полный экран' },
        { label: 'Инструменты разработчика', accelerator: 'F12', click: W((w) => w.active?.view.webContents.toggleDevTools()) },
      ],
    },
    {
      label: 'Закладки',
      submenu: [
        { label: 'Добавить в закладки', accelerator: 'CmdOrCtrl+D', click: W((w) => w.ui.send('bookmark:toggle')) },
        { label: 'Все закладки', accelerator: 'CmdOrCtrl+Shift+O', click: W((w) => w.newTab('pit://bookmarks')) },
        { label: 'История', accelerator: 'CmdOrCtrl+H', click: W((w) => w.newTab('pit://history')) },
        { label: 'Загрузки', accelerator: 'CmdOrCtrl+J', click: W((w) => w.newTab('pit://downloads')) },
        { label: 'Настройки', accelerator: 'CmdOrCtrl+,', click: W((w) => w.newTab('pit://settings')) },
      ],
    },
  ];
  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

// ---------------------------------------------------------------- запуск

app.setName('PitBrowser');
if (!app.requestSingleInstanceLock()) {
  app.quit();
} else {
  app.on('second-instance', (_e, argv) => {
    const url = argv.find((a) => /^https?:\/\//.test(a));
    const w = focusedWin();
    if (w) { if (url) w.newTab(url); if (w.win.isMinimized()) w.win.restore(); w.win.focus(); }
    else new BrowserWin({ url });
  });

  app.whenReady().then(() => {
    store = new Store(app.getPath('userData'));
    nativeTheme.themeSource = store.get('settings').theme || 'system';
    setupSession(session.fromPartition('persist:pit'));
    registerIpc();
    buildMenu();
    new BrowserWin({ url: process.argv.find((a) => /^https?:\/\//.test(a)) });
    app.on('activate', () => { if (!windows.size) new BrowserWin(); });
  });

  app.on('window-all-closed', () => {
    store?.flush();
    if (process.platform !== 'darwin') app.quit();
  });
  app.on('before-quit', () => store?.flush());
}
