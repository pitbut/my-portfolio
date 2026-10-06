'use strict';
// Простое JSON-хранилище в папке профиля: закладки, история, настройки.

const fs = require('fs');
const path = require('path');

const HISTORY_LIMIT = 5000;
const DEFAULTS = {
  bookmarks: [],
  history: [],
  settings: { searchEngine: 'google', homePage: 'pit://newtab', showBookmarksBar: true, theme: 'system', downloadDir: '' },
};

class Store {
  constructor(dir) {
    this.file = path.join(dir, 'pitbrowser.json');
    this.data = structuredClone(DEFAULTS);
    try {
      const saved = JSON.parse(fs.readFileSync(this.file, 'utf8'));
      for (const k of Object.keys(DEFAULTS)) if (k in saved) this.data[k] = saved[k];
      this.data.settings = { ...DEFAULTS.settings, ...this.data.settings };
    } catch { /* первый запуск */ }
    this.timer = null;
  }

  get(key) { return this.data[key]; }
  set(key, value) { this.data[key] = value; this.save(); }

  save() {
    clearTimeout(this.timer);
    this.timer = setTimeout(() => this.flush(), 500);
  }

  flush() {
    clearTimeout(this.timer);
    try {
      fs.mkdirSync(path.dirname(this.file), { recursive: true });
      const tmp = this.file + '.tmp';
      fs.writeFileSync(tmp, JSON.stringify(this.data));
      fs.renameSync(tmp, this.file);
    } catch (e) { console.error('store:', e.message); }
  }

  // --- закладки
  isBookmarked(url) { return this.data.bookmarks.some((b) => b.url === url); }
  toggleBookmark(b) {
    if (this.isBookmarked(b.url)) this.removeBookmark(b.url);
    else { this.data.bookmarks.push({ url: b.url, title: b.title || b.url, favicon: b.favicon || null, added: Date.now() }); this.save(); }
  }
  removeBookmark(url) { this.data.bookmarks = this.data.bookmarks.filter((b) => b.url !== url); this.save(); }

  // --- история
  addHistory({ url, title, favicon }) {
    const h = this.data.history;
    const last = h[0];
    if (last && last.url === url) { last.title = title; last.time = Date.now(); last.favicon = favicon || last.favicon; }
    else h.unshift({ url, title, favicon: favicon || null, time: Date.now() });
    if (h.length > HISTORY_LIMIT) h.length = HISTORY_LIMIT;
    this.save();
  }
  searchHistory(q) {
    const s = String(q || '').toLowerCase().trim();
    const list = s ? this.data.history.filter((x) => x.url.toLowerCase().includes(s) || (x.title || '').toLowerCase().includes(s)) : this.data.history;
    return list.slice(0, 500);
  }
  removeHistory(url) { this.data.history = this.data.history.filter((x) => x.url !== url); this.save(); }
  clearHistory() { this.data.history = []; this.save(); }

  // Подсказки адресной строки: закладки + часто посещаемое.
  suggest(q) {
    const s = String(q || '').toLowerCase().trim();
    if (!s) return [];
    const seen = new Set();
    const out = [];
    const add = (x, kind) => {
      if (seen.has(x.url) || out.length >= 8) return;
      if (!x.url.toLowerCase().includes(s) && !(x.title || '').toLowerCase().includes(s)) return;
      seen.add(x.url);
      out.push({ url: x.url, title: x.title, kind });
    };
    for (const b of this.data.bookmarks) add(b, 'bookmark');
    const counts = new Map();
    for (const h of this.data.history) counts.set(h.url, (counts.get(h.url) || 0) + 1);
    const ranked = [...new Map(this.data.history.map((h) => [h.url, h])).values()]
      .sort((a, b) => counts.get(b.url) - counts.get(a.url));
    for (const h of ranked) add(h, 'history');
    return out;
  }
}

module.exports = Store;
