'use strict';
// Загружается в каждую вкладку, но API открывает только внутренним страницам pit://.
const { contextBridge, ipcRenderer } = require('electron');

if (location.protocol === 'pit:') {
  const invoke = (ch) => (...a) => ipcRenderer.invoke(ch, ...a);
  contextBridge.exposeInMainWorld('pit', {
    bookmarks: invoke('data:bookmarks'),
    addBookmark: invoke('bookmarks:add'),
    removeBookmark: invoke('bookmarks:remove'),
    history: invoke('data:history'),
    removeHistory: invoke('history:remove'),
    clearHistory: invoke('history:clear'),
    downloads: invoke('data:downloads'),
    openDownload: invoke('downloads:open'),
    showDownload: invoke('downloads:show'),
    cancelDownload: invoke('downloads:cancel'),
    clearDownloads: invoke('downloads:clear'),
    settings: invoke('data:settings'),
    setSettings: invoke('settings:set'),
    pickDownloadDir: invoke('settings:pickDownloadDir'),
    clearBrowsingData: invoke('data:clearBrowsing'),
    open: invoke('nav:open'),
    on: (ch, fn) => {
      if (['bookmarks', 'downloads', 'settings'].includes(ch)) ipcRenderer.on(ch, (_e, v) => fn(v));
    },
  });
}
