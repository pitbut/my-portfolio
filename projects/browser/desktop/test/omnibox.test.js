'use strict';
const test = require('node:test');
const assert = require('node:assert');
const { toUrl } = require('../src/omnibox');

test('адреса', () => {
  assert.equal(toUrl('example.com'), 'https://example.com');
  assert.equal(toUrl('  sub.site.uz/path?a=1 '), 'https://sub.site.uz/path?a=1');
  assert.equal(toUrl('https://a.b/c'), 'https://a.b/c');
  assert.equal(toUrl('localhost:3000'), 'http://localhost:3000');
  assert.equal(toUrl('192.168.1.1'), 'http://192.168.1.1');
  assert.equal(toUrl('сайт.рф'), 'https://сайт.рф');
  assert.equal(toUrl('pit://history'), 'pit://history');
});

test('поиск', () => {
  assert.equal(toUrl('погода ташкент'), 'https://www.google.com/search?q=%D0%BF%D0%BE%D0%B3%D0%BE%D0%B4%D0%B0%20%D1%82%D0%B0%D1%88%D0%BA%D0%B5%D0%BD%D1%82');
  assert.equal(toUrl('hello', 'duckduckgo'), 'https://duckduckgo.com/?q=hello');
  assert.equal(toUrl('node.js tutorial'), 'https://www.google.com/search?q=node.js%20tutorial');
  assert.equal(toUrl('?example.com', 'bing'), 'https://www.bing.com/search?q=example.com');
  assert.equal(toUrl('version 1.2'), 'https://www.google.com/search?q=version%201.2');
  assert.equal(toUrl('3.14'), 'https://www.google.com/search?q=3.14');
  assert.equal(toUrl(''), null);
});
