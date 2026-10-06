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

  // ---------------------------------------------------------------- кнопки (гарнитура, громкость)

  var MEDIA = { play_pause: 1, play: 1, pause: 1, next: 1, previous: 1, stop: 1, fast_forward: 1, rewind: 1 };
  var VOLUME = { volume_up: 1, volume_down: 1 };
  // клавиши компьютера → кнопки (для отладки в обычном браузере)
  var WEB_KEYS = {
    MediaPlayPause: 'play_pause', MediaPlay: 'play', MediaPause: 'pause', MediaTrackNext: 'next',
    MediaTrackPrevious: 'previous', MediaStop: 'stop', AudioVolumeUp: 'volume_up', AudioVolumeDown: 'volume_down',
  };
  var captureCount = {};

  function captureButtons(method, kinds, fn) {
    var off = on('button', function (e) { if (kinds[e.button]) fn(e); });
    captureCount[method] = (captureCount[method] || 0) + 1;
    if (captureCount[method] === 1 && native) call(method, { enable: true }).catch(function (e) { emit('error', e); });
    return function () {
      off();
      if (--captureCount[method] === 0 && native) call(method, { enable: false }).catch(function () {});
    };
  }

  if (!native) {
    ['keydown', 'keyup'].forEach(function (type) {
      window.addEventListener(type, function (e) {
        var b = WEB_KEYS[e.key];
        if (b && !e.repeat) emit('button', { button: b, action: type === 'keydown' ? 'down' : 'up', source: 'keyboard' });
      });
    });
  }

  // ---------------------------------------------------------------- Bluetooth

  // Байты ⇄ base64 (так данные передаются между игрой и браузером).
  function toBytes(data) {
    if (typeof data === 'string') return new TextEncoder().encode(data);
    if (data instanceof Uint8Array) return data;
    if (data instanceof ArrayBuffer) return new Uint8Array(data);
    if (ArrayBuffer.isView(data)) return new Uint8Array(data.buffer, data.byteOffset, data.byteLength);
    if (Array.isArray(data)) return Uint8Array.from(data);
    throw new Error('PitSDK: данные — строка, массив чисел, Uint8Array или ArrayBuffer');
  }
  function toB64(data) {
    var b = toBytes(data), s = '';
    for (var i = 0; i < b.length; i++) s += String.fromCharCode(b[i]);
    return btoa(s);
  }
  function fromB64(b64) {
    var s = atob(b64 || ''), b = new Uint8Array(s.length);
    for (var i = 0; i < s.length; i++) b[i] = s.charCodeAt(i);
    return b;
  }
  function devId(d) { return typeof d === 'string' ? d : d && d.id; }
  function uuid(u) { return typeof u === 'number' ? u.toString(16).padStart(4, '0') : String(u); }

  function makeBluetooth() {
    function need() { if (!native) throw new Error('Bluetooth доступен только в приложении, установленном в PitBrowser'); }
    function bt(method, params) {
      try { need(); } catch (e) { return Promise.reject(e); }
      return call('bluetooth.' + method, params);
    }
    function decode(handler) {
      return function (e) { handler(Object.assign({}, e, { value: fromB64(e.value) })); };
    }
    return {
      /** { supported, enabled, ble, classic } */
      status: function () {
        return native ? bt('status') : Promise.resolve({ supported: false, enabled: false, ble: false, classic: false });
      },
      /** Попросить пользователя включить Bluetooth. */
      enable: function () { return bt('enable'); },
      /**
       * Окно выбора BLE-устройства. opts: { services: ['heart_rate', '180f', 0x180d, '6e400001-…'], namePrefix: 'ESP32' }
       * → { id, name, type: 'ble' }. Приложение получает доступ только к выбранному устройству.
       */
      requestDevice: function (opts) {
        opts = opts || {};
        return bt('requestDevice', { services: (opts.services || []).map(uuid), namePrefix: opts.namePrefix || '' });
      },
      /** Устройства, которые пользователь уже выбирал для этого приложения. */
      getDevices: function () { return native ? bt('getDevices') : Promise.resolve([]); },
      /** Подключиться → { device, services: [{ uuid, characteristics: [{ uuid, properties }] }] } */
      connect: function (device) { return bt('connect', { device: devId(device) }); },
      disconnect: function (device) { return bt('disconnect', { device: devId(device) }); },
      /** Прочитать характеристику → Uint8Array */
      read: function (device, service, characteristic) {
        return bt('read', { device: devId(device), service: uuid(service), characteristic: uuid(characteristic) }).then(fromB64);
      },
      /** Записать: строка (UTF-8), массив байт, Uint8Array или ArrayBuffer; до 512 байт за раз. */
      write: function (device, service, characteristic, data, opts) {
        return bt('write', {
          device: devId(device), service: uuid(service), characteristic: uuid(characteristic),
          value: toB64(data), withoutResponse: !!(opts && opts.withoutResponse),
        });
      },
      /** Подписаться на изменения характеристики: fn({ device, service, characteristic, value: Uint8Array }). */
      subscribe: function (device, service, characteristic, fn) {
        var id = devId(device), s = uuid(service), c = uuid(characteristic);
        // браузер вернёт UUID в единой записи ('2a37'); события до ответа придержим
        var norm = null, early = [];
        var off = on('bluetooth:notify', decode(function (e) {
          if (e.device !== id) return;
          if (norm === null) early.push(e);
          else if (e.characteristic === norm) fn(e);
        }));
        return bt('notifications', { device: id, service: s, characteristic: c, enable: true }).then(function (u) {
          norm = u;
          early.forEach(function (e) { if (e.characteristic === norm) fn(e); });
          early = [];
          return function unsubscribe() {
            off();
            return bt('notifications', { device: id, service: s, characteristic: c, enable: false }).catch(function () {});
          };
        }, function (err) { off(); throw err; });
      },
      /** Устройство отключилось: fn({ device }) */
      onDisconnect: function (fn) { return on('bluetooth:disconnected', fn); },

      /** Классический Bluetooth — последовательный порт (HC-05, HC-06, ESP32 BluetoothSerial). */
      serial: {
        /** Выбор из сопряжённых устройств → { id, name, type: 'serial' } */
        requestDevice: function () { return bt('serial.requestDevice'); },
        connect: function (device) { return bt('serial.connect', { device: devId(device) }); },
        write: function (device, data) { return bt('serial.write', { device: devId(device), value: toB64(data) }); },
        disconnect: function (device) { return bt('serial.disconnect', { device: devId(device) }); },
        /** Входящие данные: fn({ device, value: Uint8Array, text }) */
        onData: function (fn) {
          return on('bluetooth:serial', decode(function (e) {
            e.text = new TextDecoder().decode(e.value);
            fn(e);
          }));
        },
      },

      /** Помощники: байты ⇄ текст. */
      text: function (bytes) { return new TextDecoder().decode(toBytes(bytes)); },
      bytes: toBytes,
    };
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

    bluetooth: makeBluetooth(),

    headphones: {
      /** { connected, devices: [{ type: 'wired'|'bluetooth'|'usb'|'hearing_aid', name, microphone }] } */
      state: function () {
        return native ? call('headphones.state') : Promise.resolve({ connected: false, devices: [], supported: false });
      },
      /** Наушники подключили/отключили: fn({ connected, devices, change: 'connected'|'disconnected' }) */
      on: function (fn) { return on('headphones', fn); },
      /** Наушники выдернули — самое время поставить звук на паузу, чтобы он не заиграл из динамика. */
      onUnplug: function (fn) { return on('headphones:unplugged', fn); },
      /**
       * Кнопки гарнитуры (проводной и Bluetooth): fn({ button, action, source }).
       * button: play_pause, play, pause, next, previous, stop, fast_forward, rewind; action: down | up.
       * Пока есть подписчики, эти кнопки достаются игре, а не музыкальному плееру.
       */
      onButton: function (fn) { return captureButtons('headphones.captureButtons', MEDIA, fn); },
    },

    buttons: {
      /**
       * Кнопки громкости телефона как игровые: fn({ button: 'volume_up'|'volume_down', action: 'down'|'up' }).
       * Пока есть подписчики, громкость этими кнопками не меняется.
       */
      onVolume: function (fn) { return captureButtons('buttons.captureVolume', VOLUME, fn); },
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
