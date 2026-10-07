'use strict';
// Мост между панелью браузера (src/ui) и главным процессом.
const { contextBridge, ipcRenderer } = require('electron');

const send = (ch) => (...a) => ipcRenderer.send(ch, ...a);
const listen = (ch) => (fn) => ipcRenderer.on(ch, (_e, v) => fn(v));

contextBridge.exposeInMainWorld('browser', {
  platform: process.platform,
  newTab: send('tab:new'),
  closeTab: send('tab:close'),
  activateTab: send('tab:activate'),
  moveTab: send('tab:move'),
  go: send('nav:go'),
  back: send('nav:back'),
  forward: send('nav:forward'),
  reload: send('nav:reload'),
  stop: send('nav:stop'),
  home: send('nav:home'),
  setChromeHeight: send('ui:chromeHeight'),
  focusPage: send('ui:focusPage'),
  find: send('find'),
  stopFind: send('find:stop'),
  zoom: send('zoom'),
  toggleBookmark: send('bookmark:toggle'),
  newWindow: send('window:new'),
  newPrivateWindow: send('window:private'),
  bookmarks: () => ipcRenderer.invoke('data:bookmarks'),
  settings: () => ipcRenderer.invoke('data:settings'),
  suggest: (q) => ipcRenderer.invoke('data:suggest', q),
  onTabs: listen('tabs'),
  onBookmarks: listen('bookmarks'),
  onSettings: listen('settings'),
  onDownloads: listen('downloads'),
  onZoom: listen('zoom'),
  onFindResult: listen('find:result'),
  onFindOpen: listen('find:open'),
  onFocusAddress: listen('focus:address'),
  onBookmarkToggle: listen('bookmark:toggle'),
});
