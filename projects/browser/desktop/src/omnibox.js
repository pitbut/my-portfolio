'use strict';
// Разбор ввода адресной строки: адрес или поисковый запрос.
// Та же логика повторена в android/.../Omnibox.kt — меняйте обе.

const SEARCH_ENGINES = {
  google: { name: 'Google', url: 'https://www.google.com/search?q=%s' },
  duckduckgo: { name: 'DuckDuckGo', url: 'https://duckduckgo.com/?q=%s' },
  bing: { name: 'Bing', url: 'https://www.bing.com/search?q=%s' },
  yandex: { name: 'Яндекс', url: 'https://yandex.ru/search/?text=%s' },
};

const SCHEME = /^(https?|file|pit|about|data|view-source|chrome):/i;
const HOST_PORT = /^[\w.-]+:\d{1,5}(\/|$)/;
const IPV4 = /^\d{1,3}(\.\d{1,3}){3}(:\d+)?(\/|$)/;

function searchUrl(query, engine) {
  const e = SEARCH_ENGINES[engine] || SEARCH_ENGINES.google;
  return e.url.replace('%s', encodeURIComponent(query));
}

function looksLikeHost(s) {
  if (/\s/.test(s)) return false;
  if (/^localhost(:\d+)?(\/|$)/i.test(s) || IPV4.test(s) || HOST_PORT.test(s)) return true;
  const host = s.split(/[/?#]/)[0];
  // домен с точкой и буквенной зоной: example.com, сайт.рф, sub.site.uz/path
  return /^[^.\s]+(\.[^.\s]+)*\.[\p{L}]{2,}[\p{L}\d-]*$/u.test(host) || /^\[[\da-f:]+\](:\d+)?$/i.test(host);
}

/** @returns {string|null} */
function toUrl(input, engine = 'google', forceSearch = false) {
  const s = String(input ?? '').trim();
  if (!s) return null;
  if (forceSearch) return searchUrl(s, engine);
  if (s.startsWith('?')) return searchUrl(s.slice(1).trim(), engine);
  if (SCHEME.test(s) && !/\s/.test(s)) return s;
  if (looksLikeHost(s)) {
    const local = /^(localhost|127\.|10\.|192\.168\.|\[)/i.test(s);
    return (local ? 'http://' : 'https://') + s;
  }
  return searchUrl(s, engine);
}

module.exports = { toUrl, searchUrl, looksLikeHost, SEARCH_ENGINES };
