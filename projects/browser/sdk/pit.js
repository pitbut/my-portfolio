/*!
 * PitSDK — доступ к возможностям телефона для приложений и игр PitBrowser.
 * Подключение: <script src="pit.js"></script> — внутри PitBrowser браузер сам подставляет
 * актуальную версию; в обычном браузере работает запасной режим (для отладки на компьютере).
 * Документация: projects/browser/sdk/README.md
 */
(function () {
  'use strict';
  if (window.pit && window.pit.version) return;

  var VERSION = '1.0.0';
  var native = window.pitNative || null;   // мост, который PitBrowser даёт только установленным приложениям
  var seq = 0;
  var pending = {};
  var listeners = {};                      // событие → [fn]
  var info = null;

  function emit(event, data) {
    (listeners[event] || []).slice().forEach(function (fn) {
      try { fn(data); } catch (e) { setTimeout(function () { throw e; }); }
    });
  }

  function on(event, fn) {
    (listeners[event] = listeners[event] || []).push(fn);
    return function off() {
      var l = listeners[event] || [];
      var i = l.indexOf(fn);
      if (i >= 0) l.splice(i, 1);
    };
  }

  function call(method, params) {
    if (!native) return Promise.reject(new Error('PitSDK: нет связи с PitBrowser'));
    return new Promise(function (resolve, reject) {
      var id = ++seq;
      pending[id] = { resolve: resolve, reject: reject };
      native.postMessage(JSON.stringify({ id: id, method: method, params: params || {} }));
    });
  }

  if (native) {
    native.onmessage = function (e) {
      var msg;
      try { msg = JSON.parse(e.data); } catch (err) { return; }
      if (msg.id && pending[msg.id]) {
        var p = pending[msg.id];
        delete pending[msg.id];
        if (msg.error) p.reject(new Error(msg.error)); else p.resolve(msg.result);
      } else if (msg.event) {
        emit(msg.event, msg.data);
      }
    };
  }

  // ---------------------------------------------------------------- запасной режим (обычный браузер)

  var fallback = {
    key: 'pit:' + location.pathname.replace(/[^/]*$/, ''),
    load: function () { try { return JSON.parse(localStorage.getItem(this.key) || '{}'); } catch (e) { return {}; } },
    save: function (d) { try { localStorage.setItem(this.key, JSON.stringify(d)); } catch (e) { /* приватный режим */ } },
  };

  function fallbackSubmit(score, opts) {
    var d = fallback.load();
    var order = (opts && opts.order) || 'desc';
    var level = (opts && opts.level) || null;
    var list = d.scores || [];
    var prev = list.filter(function (s) { return s.level === level; })[0];
    var entry = { score: score, player: d.player || 'Игрок', time: Date.now(), level: level };
    list.push(entry);
    list.sort(function (a, b) { return (order === 'asc' ? a.score - b.score : b.score - a.score) || a.time - b.time; });
    d.scores = list.slice(0, 100);
    fallback.save(d);
    var same = d.scores.filter(function (s) { return s.level === level; });
    var isRecord = !prev || (order === 'asc' ? score < prev.score : score > prev.score);
    return { best: same[0] || null, rank: same.indexOf(entry) + 1, isRecord: isRecord };
  }

  var webSensors = {
    // датчик → [событие браузера, функция преобразования]
    accelerometer: ['devicemotion', function (e) { var a = e.accelerationIncludingGravity; return a && a.x != null ? [a.x, a.y, a.z] : null; }],
    linear_acceleration: ['devicemotion', function (e) { var a = e.acceleration; return a && a.x != null ? [a.x, a.y, a.z] : null; }],
    gyroscope: ['devicemotion', function (e) { var r = e.rotationRate; var k = Math.PI / 180; return r && r.alpha != null ? [r.beta * k, r.gamma * k, r.alpha * k] : null; }],
    orientation: ['deviceorientation', function (e) { return e.alpha != null ? [e.alpha, e.beta, e.gamma] : null; }],
  };

  // ---------------------------------------------------------------- датчики

  var sensorSubs = {}; // тип → { count, stop }

  function startSensor(type, hz) {
    if (native) {
      call('sensors.start', { type: type, hz: hz }).catch(function (e) { emit('error', e); });
      return function () { call('sensors.stop', { type: type }).catch(function () {}); };
    }
    var spec = webSensors[type];
    if (!spec) return function () {};
    var last = 0;
    var minGap = 1000 / hz;
    var handler = function (e) {
      var now = performance.now();
      if (now - last < minGap) return;
      var values = spec[1](e);
      if (!values) return;
      last = now;
      emit('sensor:' + type, { type: type, values: values, timestamp: now, rotation: screenRotation() });
    };
    window.addEventListener(spec[0], handler);
    return function () { window.removeEventListener(spec[0], handler); };
  }

  function screenRotation() {
    var a = screen.orientation ? screen.orientation.angle : window.orientation;
    return ((a || 0) % 360 + 360) % 360;
  }

  // ---------------------------------------------------------------- публичный API

  var pit = {
    version: VERSION,
    /** true — запущено внутри PitBrowser как установленное приложение. */
    isNative: !!native,

    /** Ждать готовности: возвращает сведения о приложении и игроке. */
    ready: null,

    on: on,

    app: {
      info: function () { return pit.ready; },
      /** Закрыть приложение и вернуться на главный экран PitBrowser. */
      exit: function () { return native ? call('app.exit') : (history.length > 1 ? history.back() : undefined); },
      /**
       * Своя обработка кнопки «Назад» (например, пауза в игре).
       * Без обработчика «Назад» закрывает приложение.
       */
      onBack: function (fn) {
        var off = on('back', fn);
        if (native) call('app.captureBack', { enabled: true });
        return function () {
          off();
          if (native && !(listeners.back || []).length) call('app.captureBack', { enabled: false });
        };
      },
    },

    permissions: {
      /** Запросить разрешения: ['camera', 'microphone', 'geolocation'] → { camera: true, ... } */
      request: function (names) {
        if (!native) {
          var r = {};
          (names || []).forEach(function (n) { r[n] = true; });
          return Promise.resolve(r);
        }
        return call('permissions.request', { names: names || [] });
      },
      query: function (name) { return native ? call('permissions.query', { name: name }) : Promise.resolve('granted'); },
    },

    sensors: {
      /** Список датчиков телефона: ['accelerometer', 'gyroscope', ...] */
      available: function () {
        if (native) return call('sensors.list');
        var list = [];
        if ('DeviceMotionEvent' in window) list.push('accelerometer', 'linear_acceleration', 'gyroscope');
        if ('DeviceOrientationEvent' in window) list.push('orientation');
        return Promise.resolve(list);
      },
      /**
       * Подписка на датчик. fn получает { type, values, timestamp, rotation }.
       * type: accelerometer, gyroscope, magnetometer, gravity, linear_acceleration,
       *       rotation_vector, orientation, light, proximity, pressure
       * Возвращает функцию отписки.
       */
      on: function (type, fn, opts) {
        var hz = Math.max(1, Math.min(100, (opts && opts.hz) || 60));
        var off = on('sensor:' + type, fn);
        var sub = sensorSubs[type];
        if (!sub) sub = sensorSubs[type] = { count: 0, stop: startSensor(type, hz) };
        sub.count++;
        return function () {
          off();
          if (--sub.count === 0) { sub.stop(); delete sensorSubs[type]; }
        };
      },
    },

    /** Вибрация: число (мс) или узор [вибрация, пауза, вибрация, ...]. */
    vibrate: function (pattern) {
      var p = Array.isArray(pattern) ? pattern : [pattern || 50];
      if (native) return call('vibrate', { pattern: p });
      if (navigator.vibrate) navigator.vibrate(p);
      return Promise.resolve();
    },

    screen: {
      /** Не давать экрану гаснуть (для игр с управлением наклоном). */
      keepOn: function (on) { return native ? call('screen.keepOn', { on: on !== false }) : Promise.resolve(); },
      /** 'portrait' | 'landscape' | 'any' */
      orientation: function (o) {
        if (native) return call('screen.orientation', { orientation: o });
        if (screen.orientation && screen.orientation.lock && o !== 'any') return screen.orientation.lock(o).catch(function () {});
        return Promise.resolve();
      },
      rotation: screenRotation,
    },

    player: {
      /** Имя игрока (браузер спросит один раз и запомнит). */
      name: function () {
        if (native) return call('player.name');
        return Promise.resolve(fallback.load().player || 'Игрок');
      },
    },

    scores: {
      /**
       * Записать результат. opts: { level } — отдельная таблица для уровня.
       * → { best, rank, isRecord }: rank — место в таблице (0 — не попал), isRecord — новый личный рекорд.
       */
      submit: function (score, opts) {
        if (typeof score !== 'number' || !isFinite(score)) return Promise.reject(new Error('score должен быть числом'));
        if (native) return call('scores.submit', { score: score, level: opts && opts.level });
        return pit.ready.then(function () { return fallbackSubmit(score, { level: opts && opts.level, order: info.scoreOrder }); });
      },
      /** Лучшие результаты: [{ score, player, time, level }] */
      top: function (opts) {
        var limit = (opts && opts.limit) || 10;
        var level = (opts && opts.level) || null;
        if (native) return call('scores.top', { limit: limit, level: level });
        return Promise.resolve((fallback.load().scores || []).filter(function (s) { return s.level === level; }).slice(0, limit));
      },
      best: function (opts) {
        return pit.scores.top({ limit: 1, level: opts && opts.level }).then(function (l) { return l[0] || null; });
      },
    },
  };

  pit.ready = native
    ? call('hello', { sdk: VERSION }).then(function (r) { info = r; return r; })
    : fetch('manifest.json').then(function (r) { return r.ok ? r.json() : {}; }).catch(function () { return {}; }).then(function (m) {
      // в обычном браузере берём настройки из manifest.json рядом со страницей, если он есть
      return (info = {
        id: m.id || 'dev', name: m.name || document.title, version: m.version || 'dev', native: false, platform: 'web',
        scoreOrder: (m.scores && m.scores.order) || 'desc', scoreUnit: (m.scores && m.scores.unit) || '',
        permissions: m.permissions || [], player: fallback.load().player || 'Игрок',
      });
    });

  // Игра на паузе, когда приложение свёрнуто (и в обычном браузере тоже).
  document.addEventListener('visibilitychange', function () {
    if (!native) emit(document.hidden ? 'pause' : 'resume');
  });

  window.pit = pit;
})();
