'use strict';
// Панель браузера: вкладки, адресная строка, закладки, поиск по странице.

const B = window.browser;
const $ = (id) => document.getElementById(id);
const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };

const isPrivate = new URLSearchParams(location.search).get('private') === '1';
document.body.classList.toggle('private', isPrivate);
document.body.classList.toggle('mac', B.platform === 'darwin');

let state = { tabs: [], activeId: null };
let editing = false;          // пользователь печатает в адресной строке
let suggestions = [];
let selected = -1;

const active = () => state.tabs.find((t) => t.id === state.activeId);

// --- высота панели → главный процесс сдвигает страницу
new ResizeObserver(() => B.setChromeHeight($('chrome').getBoundingClientRect().height)).observe($('chrome'));

// --- вкладки
function renderTabs() {
  const box = $('tabs');
  box.textContent = '';
  const width = box.parentElement.clientWidth - 90;
  const narrow = state.tabs.length * 100 > width;
  for (const t of state.tabs) {
    const tab = el('div', 'tab' + (t.id === state.activeId ? ' active' : '') + (narrow ? ' narrow' : ''));
    tab.title = t.title + (t.url ? '\n' + t.url : '');
    tab.draggable = true;
    tab.dataset.id = t.id;
    let fav;
    if (t.loading) fav = el('div', 'fav spin');
    else if (t.favicon) { fav = el('img', 'fav'); fav.src = t.favicon; fav.onerror = () => { fav.replaceWith(el('div', 'fav')); }; }
    else fav = el('div', 'fav', '🌐');
    const close = el('button', 'close', '✕');
    close.title = 'Закрыть вкладку (Ctrl+W)';
    close.onclick = (e) => { e.stopPropagation(); B.closeTab(t.id); };
    tab.append(fav, el('span', 'title', t.title || 'Новая вкладка'), close);
    tab.onmousedown = (e) => { if (e.button === 0) B.activateTab(t.id); };
    tab.onauxclick = (e) => { if (e.button === 1) B.closeTab(t.id); };
    tab.ondragstart = (e) => { e.dataTransfer.setData('text/tab', String(t.id)); tab.classList.add('dragging'); };
    tab.ondragend = () => tab.classList.remove('dragging');
    tab.ondragover = (e) => e.preventDefault();
    tab.ondrop = (e) => {
      e.preventDefault();
      const id = Number(e.dataTransfer.getData('text/tab'));
      if (id && id !== t.id) B.moveTab(id, state.tabs.findIndex((x) => x.id === t.id));
    };
    box.append(tab);
  }
}

function renderToolbar() {
  const t = active();
  if (!t) return;
  $('back').disabled = !t.canBack;
  $('forward').disabled = !t.canForward;
  $('reload').textContent = t.loading ? '✕' : '⟳';
  $('reload').title = t.loading ? 'Остановить' : 'Обновить (Ctrl+R)';
  if (!editing) $('address').value = t.url;
  const lock = $('lock');
  lock.hidden = !t.url;
  lock.textContent = t.secure ? '🔒' : '⚠';
  lock.classList.toggle('insecure', !t.secure);
  lock.title = t.secure ? 'Защищённое соединение' : 'Соединение не защищено';
  $('star').textContent = t.bookmarked ? '★' : '☆';
  $('star').classList.toggle('on', t.bookmarked);
  $('star').hidden = !/^https?:/.test(t.url);
}

B.onTabs((s) => {
  const switched = s.activeId !== state.activeId;
  state = s;
  if (switched) { editing = false; hideSuggestions(); closeFind(); }
  renderTabs();
  renderToolbar();
  const t = active();
  if (switched && t && !t.url) setTimeout(() => focusAddress(), 50); // новая вкладка → курсор в адресную строку
});
window.addEventListener('resize', renderTabs);

$('newtab').onclick = () => B.newTab();
$('tabstrip').ondblclick = (e) => { if (e.target.classList.contains('drag')) B.newTab(); };
$('back').onclick = () => B.back();
$('forward').onclick = () => B.forward();
$('reload').onclick = (e) => (active()?.loading ? B.stop() : B.reload(e.shiftKey));
$('home').onclick = () => B.home();
$('star').onclick = () => B.toggleBookmark();
B.onBookmarkToggle(() => B.toggleBookmark());
$('downloads').onclick = () => { $('dlbadge').hidden = true; B.newTab('pit://downloads'); };

// --- адресная строка и подсказки
const address = $('address');
function focusAddress() { address.focus(); address.select(); }
B.onFocusAddress(focusAddress);

address.addEventListener('focus', () => { editing = true; setTimeout(() => address.select(), 0); });
address.addEventListener('blur', () => setTimeout(() => { editing = false; hideSuggestions(); renderToolbar(); }, 150));
address.addEventListener('input', async () => {
  const q = address.value;
  const list = q.trim() ? await B.suggest(q) : [];
  if (address.value !== q) return;
  suggestions = list;
  selected = -1;
  renderSuggestions();
});
address.addEventListener('keydown', (e) => {
  if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
    if (!suggestions.length) return;
    e.preventDefault();
    // -1 = собственный ввод, 0..n-1 = подсказки; по кругу
    const n = suggestions.length + 1;
    selected = ((selected + 1 + (e.key === 'ArrowDown' ? 1 : -1) + n) % n) - 1;
    renderSuggestions();
  } else if (e.key === 'Escape') {
    address.value = active()?.url || '';
    hideSuggestions();
    B.focusPage();
  }
});
$('omnibox').addEventListener('submit', (e) => {
  e.preventDefault();
  const v = selected >= 0 ? suggestions[selected].url : address.value;
  hideSuggestions();
  editing = false;
  if (v.trim()) B.go(v);
});

function renderSuggestions() {
  const ul = $('suggestions');
  ul.textContent = '';
  suggestions.forEach((s, i) => {
    const li = el('li', i === selected ? 'sel' : '');
    li.append(el('span', '', s.kind === 'bookmark' ? '★' : '🕘'), el('span', 't', s.title || s.url), el('span', 'u', s.url));
    li.onmousedown = (e) => { e.preventDefault(); hideSuggestions(); editing = false; B.go(s.url); };
    ul.append(li);
  });
  ul.hidden = !suggestions.length;
}
function hideSuggestions() { suggestions = []; selected = -1; $('suggestions').hidden = true; }

// --- меню
const menu = $('menupanel');
$('menu').onclick = () => { menu.hidden = !menu.hidden; };
menu.onclick = (e) => {
  const b = e.target.closest('button');
  if (!b) return;
  const cmd = b.dataset.cmd;
  if (b.dataset.url) B.newTab(b.dataset.url);
  else if (cmd === 'newtab') B.newTab();
  else if (cmd === 'newwindow') B.newWindow();
  else if (cmd === 'private') B.newPrivateWindow();
  else if (cmd === 'zoomin') { B.zoom(0.5); return; }
  else if (cmd === 'zoomout') { B.zoom(-0.5); return; }
  else if (cmd === 'find') openFind();
  menu.hidden = true;
};
document.addEventListener('mousedown', (e) => { if (!menu.hidden && !e.target.closest('#menupanel, #menu')) menu.hidden = true; });
B.onZoom((z) => {
  $('zoomval').textContent = z + '%';
  $('zoomlevel').textContent = z + '%';
  $('zoomlevel').hidden = z === 100;
});

// --- панель закладок
async function renderBookmarks(list) {
  const settings = await B.settings();
  const bar = $('bookmarksbar');
  bar.textContent = '';
  bar.classList.toggle('hidden', !settings.showBookmarksBar);
  for (const b of list) {
    const btn = el('button');
    btn.title = b.title + '\n' + b.url;
    if (b.favicon) { const img = el('img'); img.src = b.favicon; img.onerror = () => img.remove(); btn.append(img); }
    btn.append(el('span', '', b.title || b.url));
    btn.onclick = (e) => (e.ctrlKey || e.metaKey ? B.newTab(b.url) : B.go(b.url));
    btn.onauxclick = (e) => { if (e.button === 1) B.newTab(b.url); };
    bar.append(btn);
  }
}
B.bookmarks().then(renderBookmarks);
B.onBookmarks(renderBookmarks);
B.onSettings(() => B.bookmarks().then(renderBookmarks));

// --- загрузки
B.onDownloads((list) => { if (list.some((d) => d.state === 'progressing' || d.state === 'completed')) $('dlbadge').hidden = false; });

// --- поиск по странице
const findbar = $('findbar');
const findinput = $('findinput');
function openFind() { findbar.hidden = false; findinput.focus(); findinput.select(); if (findinput.value) B.find(findinput.value, {}); }
function closeFind() { if (findbar.hidden) return; findbar.hidden = true; $('findcount').textContent = ''; B.stopFind(); }
B.onFindOpen(openFind);
findinput.addEventListener('input', () => { if (findinput.value) B.find(findinput.value, {}); else { B.stopFind(); $('findcount').textContent = ''; } });
findbar.addEventListener('submit', (e) => { e.preventDefault(); B.find(findinput.value, { findNext: true }); });
findinput.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') { closeFind(); B.focusPage(); }
  if (e.key === 'Enter' && e.shiftKey) { e.preventDefault(); B.find(findinput.value, { findNext: true, forward: false }); }
});
$('findnext').onclick = () => B.find(findinput.value, { findNext: true });
$('findprev').onclick = () => B.find(findinput.value, { findNext: true, forward: false });
$('findclose').onclick = () => { closeFind(); B.focusPage(); };
B.onFindResult(({ active: a, total }) => { $('findcount').textContent = total ? `${a} из ${total}` : 'Нет совпадений'; });
