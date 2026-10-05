/* Путешествие к центру Земли — аркада по мотивам романа Жюля Верна.
   Чистый Canvas 2D, без зависимостей: работает в браузере и внутри Android WebView. */
(() => {
'use strict';

// ---------- Холст и масштаб ----------
const cv = document.getElementById('game');
const ctx = cv.getContext('2d');
const dark = document.createElement('canvas');
const dctx = dark.getContext('2d');
const pauseBtn = document.getElementById('pauseBtn');
const W = 360;
let H = 640, S = 1, DPR = 1;

function resize() {
  const iw = window.innerWidth, ih = window.innerHeight;
  DPR = Math.min(window.devicePixelRatio || 1, 2.5);
  H = Math.round(Math.min(800, Math.max(560, W * ih / iw)));
  S = Math.min(iw / W, ih / H);
  cv.style.width = Math.round(W * S) + 'px';
  cv.style.height = Math.round(H * S) + 'px';
  cv.width = Math.round(W * S * DPR);
  cv.height = Math.round(H * S * DPR);
  dark.width = W; dark.height = H;
  const left = (iw - W * S) / 2, top = (ih - H * S) / 2;
  pauseBtn.style.left = (left + W * S - 54) + 'px';
  pauseBtn.style.top = (top + 10) + 'px';
}
window.addEventListener('resize', resize);
resize();

// ---------- Утилиты ----------
const rand = (a, b) => a + Math.random() * (b - a);
const clamp = (v, a, b) => v < a ? a : v > b ? b : v;
const lerp = (a, b, t) => a + (b - a) * t;
const smooth = (a, b, v) => { const t = clamp((v - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); };
let seed = 1;
function hash(i) { const x = Math.sin(i * 127.1 + seed * 311.7) * 43758.5453; return x - Math.floor(x); }
function noise(t) { const i = Math.floor(t), f = t - i, u = f * f * (3 - 2 * f); return lerp(hash(i), hash(i + 1), u); }
function pick(table) {
  let sum = 0; for (const k in table) sum += table[k];
  let r = Math.random() * sum;
  for (const k in table) { r -= table[k]; if (r <= 0) return k; }
  return Object.keys(table)[0];
}

// ---------- Сохранение ----------
const SAVE_KEY = 'czemli_save_v1';
let save = { unlocked: 1, best: 0, runes: [], sound: true, won: false };
try { Object.assign(save, JSON.parse(localStorage.getItem(SAVE_KEY) || '{}')); } catch (e) {}
function persist() { try { localStorage.setItem(SAVE_KEY, JSON.stringify(save)); } catch (e) {} }

// ---------- Звук ----------
let actx = null;
function audio() {
  if (!save.sound) return null;
  if (!actx) { try { actx = new (window.AudioContext || window.webkitAudioContext)(); } catch (e) { return null; } }
  if (actx.state === 'suspended') actx.resume();
  return actx;
}
function tone(f1, f2, dur, type = 'sine', vol = 0.15) {
  const a = audio(); if (!a) return;
  const o = a.createOscillator(), gn = a.createGain(), t = a.currentTime;
  o.type = type; o.frequency.setValueAtTime(f1, t); o.frequency.exponentialRampToValueAtTime(f2, t + dur);
  gn.gain.setValueAtTime(vol, t); gn.gain.exponentialRampToValueAtTime(0.001, t + dur);
  o.connect(gn).connect(a.destination); o.start(t); o.stop(t + dur);
}
const sfx = {
  gem: () => tone(880, 1760, 0.12, 'triangle', 0.12),
  water: () => tone(300, 700, 0.18, 'sine', 0.15),
  lamp: () => tone(500, 1000, 0.2, 'square', 0.05),
  rune: () => { tone(440, 880, 0.35, 'triangle', 0.14); setTimeout(() => tone(660, 1320, 0.4, 'triangle', 0.12), 120); },
  hit: () => tone(160, 40, 0.35, 'sawtooth', 0.2),
  zap: () => tone(1200, 90, 0.3, 'square', 0.08),
};
function buzz(ms) { try { if (navigator.vibrate) navigator.vibrate(ms); } catch (e) {} }

// ---------- Главы ----------
const CH = [
  { name: 'Кратер Снайфедльса', roman: 'I', dir: 1, len: 9000, v0: 150, v1: 215, w0: 230, w1: 165, wig: 0.8,
    gap: 150, drain: 1.1, darkness: 0.93, daylight: 900, lampDrain: 1.4, rocks: 2.6,
    spawn: { spike: 4, gem: 4, water: 1.3, lamp: 1.6 },
    bg: ['#2a2420', '#120e0c'], wall: '#3b3430', strata: ['#4a423c', '#2c2622', '#57483d'], edge: '#6f645b',
    text: ['Гамбург, 1863 год. В старинной рукописи профессор Лиденброк нашёл зашифрованную записку исландского алхимика Арне Сакнуссема.',
           '«Спустись в кратер Снайфедльса, который тень Скартариса ласкает перед июльскими календами, — и ты достигнешь центра Земли».',
           'Вы — Аксель, племянник профессора. С вами дядя и невозмутимый проводник Ганс. Спускайтесь по базальтовому жерлу, не касайтесь стен и берегитесь камнепадов.'] },
  { name: 'Галереи. Жажда', roman: 'II', dir: 1, len: 10000, v0: 165, v1: 235, w0: 200, w1: 140, wig: 1,
    gap: 145, drain: 3.4, darkness: 0.95, daylight: 0, lampDrain: 1.7, rocks: 3.4,
    spawn: { spike: 5, gem: 3, water: 0.7, lamp: 1.6, stream: 1.1 },
    bg: ['#2b1c14', '#0f0906'], wall: '#4a2c1c', strata: ['#5c3826', '#3a2216', '#6b4630'], edge: '#8a5a3c',
    text: ['Вода кончилась. Несколько дней экспедиция шла по сухим гранитным галереям, и силы покидали вас.',
           'Но Ганс приложил ухо к скале и услышал шум подземного потока. Удар кирки — и из стены хлынула горячая струя. Профессор назвал её Гансбах — «ручей Ганса».',
           'Держитесь голубых струй Гансбаха — они утоляют жажду. Фляги попадаются редко.'] },
  { name: 'Море Лиденброка', roman: 'III', dir: 1, len: 11000, v0: 170, v1: 240, w0: 320, w1: 300, wig: 0.3,
    gap: 175, drain: 0.6, darkness: 0, daylight: 0, lampDrain: 0, rocks: 0,
    spawn: { ichthy: 3, plesio: 2.4, ball: 1.3, gem: 3.5, water: 0.6 }, raft: true, sea: true,
    bg: ['#1d4f63', '#0c2a38'], wall: '#3c4a3f', strata: ['#4c5c4f', '#33403a', '#5a6b5a'], edge: '#8fa58f',
    text: ['Галерея вывела к невероятному: под каменным сводом раскинулось море, залитое холодным электрическим сиянием.',
           'Из гигантских стволов Ганс связал плот. Профессор нарёк воды морем Лиденброка.',
           'В глубине проснулись ихтиозавр и плезиозавр, а над волнами блуждает шаровая молния. Правьте плотом между ними!'] },
  { name: 'Подземный лес', roman: 'IV', dir: 1, len: 10000, v0: 175, v1: 245, w0: 290, w1: 220, wig: 0.7,
    gap: 150, drain: 1.3, darkness: 0, daylight: 0, lampDrain: 0, rocks: 0,
    spawn: { shroom: 4, mastodon: 2.2, spike: 1.2, gem: 3, water: 1.2 },
    bg: ['#1f2e1a', '#0d150b'], wall: '#2e3a24', strata: ['#3b4a2e', '#26301e', '#4a5a36'], edge: '#7d955f',
    text: ['За морем — берег, усеянный костями допотопных животных, и лес из гигантских грибов и древних папоротников.',
           'Между стволами бродит стадо мастодонтов, а их пастух — великан ростом в двенадцать футов.',
           'Пробирайтесь тихо, обходите грибы и не попадайтесь мастодонтам. Где-то здесь — нож Сакнуссема и его вырезанные на скале инициалы.'] },
  { name: 'Извержение', roman: 'V', dir: -1, len: 11500, v0: 200, v1: 310, w0: 210, w1: 150, wig: 1,
    gap: 150, drain: 2.2, darkness: 0.55, daylight: 0, lampDrain: 0, rocks: 2.2,
    spawn: { spike: 3, gem: 3, water: 1.3 }, raft: true, lava: true,
    bg: ['#5a1a0a', '#1a0603'], wall: '#2a1a16', strata: ['#3a221c', '#1e1210', '#4a2a20'], edge: '#ff6a2a',
    text: ['Путь к центру преградил обвал. Порох разнёс скалу — и открыл бездну. Море хлынуло в пропасть и увлекло плот за собой.',
           'Вода кипит, стены раскалены: плот подхватил подъём лавы в жерле вулкана!',
           'Теперь — только вверх. Уворачивайтесь от раскалённых стен и лавовых бомб, летящих снизу.'] },
];
const DESC_TOTAL = CH.slice(0, 4).reduce((s, c) => s + c.len, 0);
const MAX_KM = 140;

// ---------- Состояние ----------
let state = 'menu';
let g = null;
let keys = {};

function newGame(chIndex, keepScore) {
  const prev = g;
  g = {
    ci: chIndex, c: CH[chIndex], dir: CH[chIndex].dir,
    x: W / 2, tx: W / 2, y: 0, dist: 0, speed: CH[chIndex].v0,
    hearts: 3, water: 100, lamp: 100,
    score: keepScore && prev ? prev.score : 0,
    gems: keepScore && prev ? prev.gems : 0,
    inv: 0, t: 0, thirst: 0, nextSpawn: 260, rockT: 2.5,
    objs: [], parts: [], warns: [], decor: [], hist: [], msg: null, shake: 0, flash: 0,
    runeGot: false,
  };
  seed = 1 + chIndex * 17 + Math.floor(Math.random() * 1000);
  g.hist = new Array(60).fill(W / 2);
}

function chapterStartKm(ci) {
  if (ci < 4) return CH.slice(0, ci).reduce((s, c) => s + c.len, 0) / DESC_TOTAL * MAX_KM;
  return MAX_KM;
}
function depthKm() {
  if (g.ci < 4) return chapterStartKm(g.ci) + g.dist / DESC_TOTAL * MAX_KM;
  return Math.max(0, MAX_KM * (1 - g.dist / g.c.len));
}

// ---------- Стены ----------
function wallAt(y) {
  const c = g.c, d = Math.abs(y);
  const p = clamp(d / c.len, 0, 1);
  let width = lerp(c.w0, c.w1, p) * (0.82 + 0.36 * noise(y * 0.004 + 50));
  width = lerp(W - 24, width, smooth(0, 420, d));
  const room = (W - width) / 2 - 8;
  const center = W / 2 + room * (noise(y * 0.0024) * 2 - 1) * c.wig;
  return { l: Math.max(6, center - width / 2), r: Math.min(W - 6, center + width / 2) };
}

// ---------- Объекты ----------
function spawnAt(y) {
  const c = g.c, w = wallAt(y), width = w.r - w.l;
  let type = pick(c.spawn);
  const remaining = c.len - Math.abs(y);
  if (!g.runeGot && !g.objs.some(o => o.type === 'rune') && Math.abs(y) > c.len * 0.55 && Math.random() < 0.08) type = 'rune';
  if (remaining < 500 && !g.runeGot && !g.objs.some(o => o.type === 'rune')) type = 'rune';
  const o = { type, y, x: W / 2, r: 10, dead: false, t: Math.random() * 10 };
  switch (type) {
    case 'spike': {
      const left = Math.random() < 0.5, len = Math.min(width * 0.42, rand(30, 62));
      const bx = left ? wallAt(y).l - 4 : wallAt(y).r + 4;
      o.side = left ? 1 : -1; o.bx = bx; o.tx = bx + o.side * len; o.half = 15; o.x = o.tx;
      break;
    }
    case 'gem': o.x = rand(w.l + 18, w.r - 18); o.r = 9; o.hue = [195, 140, 330, 45][Math.floor(Math.random() * 4)]; break;
    case 'water': o.x = rand(w.l + 20, w.r - 20); o.r = 11; break;
    case 'lamp': o.x = rand(w.l + 20, w.r - 20); o.r = 11; break;
    case 'rune': o.x = rand(w.l + 30, w.r - 30); o.r = 13; break;
    case 'stream': o.h = 130; o.r = 0; break;
    case 'ichthy': case 'mastodon': {
      const fromLeft = Math.random() < 0.5;
      o.vx = (fromLeft ? 1 : -1) * (type === 'ichthy' ? rand(70, 110) : rand(45, 70));
      o.x = fromLeft ? -60 : W + 60; o.r = type === 'ichthy' ? 13 : 20; o.len = type === 'ichthy' ? 70 : 54;
      break;
    }
    case 'plesio': o.x = rand(w.l + 50, w.r - 50); o.base = o.x; o.r = 12; break;
    case 'ball': o.x = rand(w.l + 30, w.r - 30); o.r = 11; break;
    case 'shroom': o.x = rand(w.l + 25, w.r - 25); o.r = rand(17, 27); o.hue = rand(15, 45); break;
  }
  g.objs.push(o);
  // декор
  if (c.sea && Math.random() < 0.5) g.decor.push({ k: 'wave', x: rand(w.l, w.r), y: y + rand(-60, 60) });
  if (g.ci === 3 && Math.random() < 0.35) g.decor.push({ k: 'fern', x: Math.random() < 0.5 ? w.l - 10 : w.r + 10, y, s: rand(0.7, 1.3) });
  if (g.ci === 3 && Math.random() < 0.03) g.decor.push({ k: 'giant', x: Math.random() < 0.5 ? 20 : W - 20, y });
  if ((g.ci === 0 || g.ci === 1) && Math.random() < 0.25) g.decor.push({ k: 'bones', x: Math.random() < 0.5 ? w.l - 14 : w.r + 14, y });
}

function addWarn(x) { g.warns.push({ x, t: 0.75 }); }

function burst(x, y, color, n = 12, sp = 120) {
  for (let i = 0; i < n; i++) {
    const a = Math.random() * Math.PI * 2, v = rand(sp * 0.3, sp);
    g.parts.push({ x, y, vx: Math.cos(a) * v, vy: Math.sin(a) * v, life: rand(0.4, 0.9), max: 0.9, color, s: rand(1.5, 3.5) });
  }
}

function say(text, color = '#ffd28a') { g.msg = { text, t: 2.2, color }; }

// ---------- Ввод ----------
let touchId = null, touchStartX = 0, touchStartTx = 0;
function toLocalX(clientX) { const rect = cv.getBoundingClientRect(); return (clientX - rect.left) / S; }
cv.addEventListener('pointerdown', e => {
  audio();
  if (state !== 'play') return;
  touchId = e.pointerId; touchStartX = toLocalX(e.clientX); touchStartTx = g.tx;
  try { cv.setPointerCapture(e.pointerId); } catch (err) {}
});
cv.addEventListener('pointermove', e => {
  if (state !== 'play' || e.pointerId !== touchId) return;
  g.tx = clamp(touchStartTx + (toLocalX(e.clientX) - touchStartX) * 1.35, 8, W - 8);
});
const endTouch = e => { if (e.pointerId === touchId) touchId = null; };
cv.addEventListener('pointerup', endTouch);
cv.addEventListener('pointercancel', endTouch);
window.addEventListener('keydown', e => {
  keys[e.key] = true;
  if ((e.key === 'Escape' || e.key === 'p' || e.key === 'з') && state === 'play') pauseGame();
  else if (e.key === 'Escape' && state === 'pause') resumeGame();
});
window.addEventListener('keyup', e => { keys[e.key] = false; });

// ---------- Обновление ----------
function hurt(reason) {
  if (g.inv > 0) return;
  g.hearts--; g.inv = 1.6; g.shake = 0.35; g.flash = 0.25;
  sfx.hit(); buzz(120);
  burst(g.x, g.y, '#ffb070', 16, 160);
  if (reason) say(reason, '#ff8a6a');
  if (g.hearts <= 0) gameOver();
}

function update(dt) {
  const c = g.c;
  g.t += dt;
  const p = clamp(g.dist / c.len, 0, 1);
  g.speed = lerp(c.v0, c.v1, p);
  const step = g.speed * dt;
  g.dist += step; g.y += g.dir * step;
  g.score += step * 0.01;

  // управление
  const kl = keys.ArrowLeft || keys.a || keys.A || keys['ф'], kr = keys.ArrowRight || keys.d || keys.D || keys['в'];
  if (kl) g.tx -= 300 * dt;
  if (kr) g.tx += 300 * dt;
  g.tx = clamp(g.tx, 8, W - 8);
  g.x += (g.tx - g.x) * Math.min(1, dt * 14);
  g.hist.unshift(g.x); g.hist.length = 60;

  // ресурсы
  g.water = Math.max(0, g.water - c.drain * dt);
  const lit = c.darkness > 0 && g.dist > c.daylight;
  if (lit) g.lamp = Math.max(0, g.lamp - c.lampDrain * dt);
  if (g.water <= 0) {
    g.thirst += dt;
    if (g.thirst > 3.5) { g.thirst = 0; g.inv = 0; hurt('Жажда! Ищите воду'); }
  } else g.thirst = 0;
  g.inv = Math.max(0, g.inv - dt);
  g.shake = Math.max(0, g.shake - dt);
  g.flash = Math.max(0, g.flash - dt);
  if (g.msg && (g.msg.t -= dt) <= 0) g.msg = null;

  // появление объектов
  while (g.dist + H > g.nextSpawn && g.nextSpawn < c.len - 250) {
    spawnAt(g.dir * g.nextSpawn);
    g.nextSpawn += c.gap * rand(0.7, 1.3) * lerp(1, 0.8, p);
  }
  // камнепад / лавовые бомбы
  if (c.rocks > 0 && g.dist > 500 && g.dist < c.len - 300) {
    g.rockT -= dt;
    if (g.rockT <= 0) {
      g.rockT = c.rocks * rand(0.6, 1.2) * lerp(1, 0.65, p);
      const w = wallAt(g.y);
      addWarn(clamp(g.x + rand(-60, 60), w.l + 14, w.r - 14));
    }
  }
  for (const wn of g.warns) {
    wn.t -= dt;
    if (wn.t <= 0) {
      const camY = cameraY();
      const sy = g.dir > 0 ? camY - 30 : camY + H + 30;
      g.objs.push({ type: c.lava ? 'bomb' : 'rock', x: wn.x, y: sy, vy: g.dir * (g.speed + 150), r: c.lava ? 10 : rand(10, 15), rot: 0, dead: false, t: 0 });
    }
  }
  g.warns = g.warns.filter(w => w.t > 0);

  // стены
  const w = wallAt(g.y), R = 10;
  if (g.x - R < w.l || g.x + R > w.r) {
    if (g.inv <= 0) {
      hurt(c.lava ? 'Раскалённая стена!' : 'Удар о скалу!');
      const mid = (w.l + w.r) / 2; g.x = g.tx = lerp(g.x, mid, 0.6);
    } else {
      g.x = g.tx = clamp(g.x, w.l + R, w.r - R);
    }
  }

  // объекты
  const camY = cameraY();
  for (const o of g.objs) {
    o.t += dt;
    switch (o.type) {
      case 'rock': case 'bomb': o.y += o.vy * dt; o.rot += dt * 4;
        if (o.type === 'bomb' && Math.random() < 0.5) g.parts.push({ x: o.x + rand(-3, 3), y: o.y + rand(-3, 3), vx: 0, vy: rand(-20, 20), life: 0.4, max: 0.4, color: '#ff8a2a', s: 2.5 });
        break;
      case 'ichthy': case 'mastodon': o.x += o.vx * dt; break;
      case 'plesio': o.x = o.base + Math.sin(o.t * 1.6) * 45; break;
      case 'ball': {
        const dx = g.x - o.x; o.x += clamp(dx, -1, 1) * 38 * dt + Math.sin(o.t * 5) * 30 * dt;
        if (Math.random() < 0.3) g.parts.push({ x: o.x + rand(-8, 8), y: o.y + rand(-8, 8), vx: rand(-30, 30), vy: rand(-30, 30), life: 0.25, max: 0.25, color: '#cfe8ff', s: 1.5 });
        break;
      }
    }
    // столкновения
    if (o.type === 'stream') {
      if ((g.y - o.y) * g.dir > 0 && (g.y - o.y) * g.dir < o.h) {
        g.water = Math.min(100, g.water + 38 * dt);
        if (!o.told) { o.told = true; say('Гансбах! Пейте вдоволь', '#8fd8ff'); sfx.water(); }
      }
      continue;
    }
    if (o.type === 'spike') {
      for (let k = 0.15; k <= 0.9; k += 0.25) {
        const px = lerp(o.bx, o.tx, k), rr = lerp(o.half, 2, k);
        if (Math.hypot(px - g.x, o.y - g.y) < rr + 8) { hurt('Сталактит!'); break; }
      }
      continue;
    }
    if (o.type === 'ichthy' || o.type === 'mastodon') {
      const back = -Math.sign(o.vx);
      for (let k = 0; k <= 1; k += 0.25) {
        const px = o.x + back * o.len * k, rr = o.r * (1 - k * 0.45);
        if (Math.hypot(px - g.x, o.y - g.y) < rr + 9) { hurt(o.type === 'ichthy' ? 'Ихтиозавр!' : 'Мастодонт!'); break; }
      }
      continue;
    }
    const d = Math.hypot(o.x - g.x, o.y - g.y);
    if (d > o.r + 10) continue;
    switch (o.type) {
      case 'gem': o.dead = true; g.gems++; g.score += 10; sfx.gem(); burst(o.x, o.y, `hsl(${o.hue},90%,70%)`, 10, 90); break;
      case 'water': o.dead = true; g.water = Math.min(100, g.water + 40); sfx.water(); burst(o.x, o.y, '#7cc8ff', 10, 90); say('Фляга воды', '#8fd8ff'); break;
      case 'lamp': o.dead = true; g.lamp = Math.min(100, g.lamp + 50); sfx.lamp(); burst(o.x, o.y, '#fff3a0', 10, 90); say('Батарея Румкорфа', '#fff0a0'); break;
      case 'rune':
        o.dead = true; g.runeGot = true; g.score += 100; sfx.rune(); burst(o.x, o.y, '#ffd28a', 24, 140);
        say('Руна Сакнуссема! «А.С.»', '#ffd28a');
        if (!save.runes.includes(g.ci)) { save.runes.push(g.ci); persist(); }
        break;
      case 'plesio': hurt('Плезиозавр!'); break;
      case 'ball': o.dead = true; sfx.zap(); burst(o.x, o.y, '#d8ecff', 24, 170); g.inv = 0; hurt('Шаровая молния!'); break;
      case 'shroom': hurt('Гигантский гриб!'); break;
      case 'rock': o.dead = true; burst(o.x, o.y, '#8a7a6a', 14, 130); hurt('Камнепад!'); break;
      case 'bomb': o.dead = true; burst(o.x, o.y, '#ff7a2a', 18, 150); hurt('Лавовая бомба!'); break;
    }
    if (state !== 'play') return;
  }
  // уборка
  const keep = o => {
    if (o.dead) return false;
    const sy = o.y - camY;
    if ((o.type === 'ichthy' || o.type === 'mastodon') && (o.x < -140 || o.x > W + 140)) return false;
    return sy > -H * 0.6 - 120 && sy < H * 1.6 + 120;
  };
  g.objs = g.objs.filter(keep);
  g.decor = g.decor.filter(d => g.dir > 0 ? d.y - camY > -200 : d.y - camY < H + 200);
  for (const pt of g.parts) { pt.x += pt.vx * dt; pt.y += pt.vy * dt; pt.life -= dt; }
  g.parts = g.parts.filter(pt => pt.life > 0);

  if (state === 'play' && g.dist >= c.len) chapterDone();
}

function cameraY() { return g.y - (g.dir > 0 ? H * 0.3 : H * 0.7); }

// ---------- Отрисовка ----------
function drawWalls(camY) {
  const c = g.c, step = 10;
  const y0 = Math.floor(camY / step) * step - step, y1 = camY + H + step;
  const L = [], Rr = [];
  for (let y = y0; y <= y1; y += step) { const w = wallAt(y); L.push([w.l, y - camY]); Rr.push([w.r, y - camY]); }
  for (const side of [L, Rr]) {
    const edgeX = side === L ? 0 : W;
    ctx.beginPath(); ctx.moveTo(edgeX, side[0][1]);
    for (const [x, y] of side) ctx.lineTo(x, y);
    ctx.lineTo(edgeX, side[side.length - 1][1]); ctx.closePath();
    ctx.fillStyle = c.wall; ctx.fill();
    ctx.save(); ctx.clip();
    // слои породы
    const band = 34, b0 = Math.floor(camY / band);
    for (let b = b0 - 1; b < b0 + H / band + 2; b++) {
      ctx.fillStyle = c.strata[((b % 3) + 3) % 3];
      const yy = b * band - camY + Math.sin(b * 1.7) * 6;
      ctx.globalAlpha = 0.55;
      ctx.beginPath();
      ctx.moveTo(0, yy);
      for (let x = 0; x <= W; x += 40) ctx.lineTo(x, yy + Math.sin(x * 0.03 + b) * 5);
      ctx.lineTo(W, yy + band * 0.45); ctx.lineTo(0, yy + band * 0.45); ctx.fill();
    }
    ctx.globalAlpha = 1;
    if (c.lava) { // раскалённые трещины
      ctx.strokeStyle = 'rgba(255,110,30,.55)'; ctx.lineWidth = 1.5;
      for (let b = b0 - 1; b < b0 + H / band + 2; b++) {
        const yy = b * band - camY;
        ctx.beginPath(); ctx.moveTo(side === L ? 0 : W, yy);
        ctx.lineTo(side === L ? 30 + hash(b) * 40 : W - 30 - hash(b) * 40, yy + 14); ctx.stroke();
      }
    }
    ctx.restore();
    ctx.beginPath();
    for (let i = 0; i < side.length; i++) i ? ctx.lineTo(side[i][0], side[i][1]) : ctx.moveTo(side[i][0], side[i][1]);
    ctx.strokeStyle = c.edge; ctx.lineWidth = c.lava ? 3 : 2;
    if (c.lava) { ctx.shadowColor = '#ff5a00'; ctx.shadowBlur = 10; }
    ctx.stroke(); ctx.shadowBlur = 0;
  }
}

function drawBackground(camY) {
  const c = g.c;
  const grd = ctx.createLinearGradient(0, 0, 0, H);
  grd.addColorStop(0, c.bg[0]); grd.addColorStop(1, c.bg[1]);
  ctx.fillStyle = grd; ctx.fillRect(0, 0, W, H);
  if (c.sea) {
    ctx.strokeStyle = 'rgba(160,220,240,.18)'; ctx.lineWidth = 1.5;
    for (let i = 0; i < 26; i++) {
      const wy = ((i * 47 - camY * 0.9) % (H + 40) + H + 40) % (H + 40) - 20;
      const wx = (i * 97) % W;
      ctx.beginPath(); ctx.arc(wx, wy, 14, Math.PI * 1.15, Math.PI * 1.85); ctx.stroke();
    }
    // электрическое сияние свода
    const gl = ctx.createRadialGradient(W / 2, -40, 10, W / 2, -40, H);
    gl.addColorStop(0, 'rgba(200,240,255,.25)'); gl.addColorStop(1, 'rgba(200,240,255,0)');
    ctx.fillStyle = gl; ctx.fillRect(0, 0, W, H);
  } else {
    // пыль в воздухе
    ctx.fillStyle = 'rgba(255,230,190,.07)';
    for (let i = 0; i < 30; i++) {
      const yy = ((i * 61 - camY * 0.5) % H + H) % H;
      ctx.fillRect((i * 113 + Math.sin(g.t + i) * 8) % W, yy, 2, 2);
    }
  }
  if (c.lava) {
    const lv = ctx.createLinearGradient(0, H * 0.75, 0, H);
    lv.addColorStop(0, 'rgba(255,90,0,0)'); lv.addColorStop(1, 'rgba(255,120,20,.85)');
    ctx.fillStyle = lv; ctx.fillRect(0, H * 0.75, W, H * 0.25);
  }
}

function drawDecor(d, sy) {
  ctx.save(); ctx.translate(d.x, sy);
  if (d.k === 'wave') {
    ctx.strokeStyle = 'rgba(220,250,255,.25)'; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.arc(0, 0, 10, Math.PI * 1.1, Math.PI * 1.9); ctx.stroke();
  } else if (d.k === 'fern') {
    ctx.scale(d.s, d.s); ctx.strokeStyle = '#5f8a3e'; ctx.lineWidth = 2;
    for (let i = -3; i <= 3; i++) { ctx.beginPath(); ctx.moveTo(0, 0); ctx.quadraticCurveTo(i * 8, -12, i * 14, -4 + Math.abs(i) * 3); ctx.stroke(); }
  } else if (d.k === 'giant') {
    ctx.globalAlpha = 0.35; ctx.fillStyle = '#0a1008';
    ctx.beginPath(); ctx.arc(0, -70, 12, 0, Math.PI * 2); ctx.fill();
    ctx.fillRect(-12, -58, 24, 50); ctx.fillRect(-10, -8, 8, 40); ctx.fillRect(2, -8, 8, 40);
    ctx.fillRect(12, -60, 4, 90);
  } else if (d.k === 'bones') {
    ctx.strokeStyle = 'rgba(230,220,200,.35)'; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(-8, -3); ctx.lineTo(8, 3); ctx.moveTo(-6, 4); ctx.lineTo(6, -4); ctx.stroke();
  }
  ctx.restore();
}

function drawObj(o, sy) {
  const x = o.x;
  ctx.save();
  switch (o.type) {
    case 'spike': {
      ctx.fillStyle = g.c.lava ? '#3a1d14' : g.c.edge; ctx.strokeStyle = 'rgba(0,0,0,.4)';
      ctx.beginPath(); ctx.moveTo(o.bx, sy - o.half); ctx.lineTo(o.tx, sy); ctx.lineTo(o.bx, sy + o.half); ctx.closePath(); ctx.fill(); ctx.stroke();
      ctx.fillStyle = 'rgba(255,255,255,.12)';
      ctx.beginPath(); ctx.moveTo(o.bx, sy - o.half); ctx.lineTo(o.tx, sy); ctx.lineTo(o.bx, sy - o.half * 0.2); ctx.fill();
      break;
    }
    case 'gem': {
      ctx.translate(x, sy); ctx.rotate(Math.sin(o.t * 2) * 0.3);
      ctx.shadowColor = `hsl(${o.hue},90%,60%)`; ctx.shadowBlur = 12;
      ctx.fillStyle = `hsl(${o.hue},80%,62%)`;
      ctx.beginPath(); ctx.moveTo(0, -10); ctx.lineTo(8, -2); ctx.lineTo(0, 10); ctx.lineTo(-8, -2); ctx.closePath(); ctx.fill();
      ctx.shadowBlur = 0; ctx.fillStyle = 'rgba(255,255,255,.55)';
      ctx.beginPath(); ctx.moveTo(0, -10); ctx.lineTo(3, -2); ctx.lineTo(-8, -2); ctx.fill();
      break;
    }
    case 'water': {
      ctx.translate(x, sy + Math.sin(o.t * 3) * 2);
      ctx.shadowColor = '#5ab8ff'; ctx.shadowBlur = 10;
      ctx.fillStyle = '#6b4a2b'; ctx.fillRect(-3, -14, 6, 5);
      ctx.fillStyle = '#4fa8e8'; ctx.beginPath(); ctx.ellipse(0, 1, 9, 11, 0, 0, Math.PI * 2); ctx.fill();
      ctx.shadowBlur = 0; ctx.fillStyle = 'rgba(255,255,255,.5)'; ctx.beginPath(); ctx.ellipse(-3, -2, 2.5, 4, 0, 0, Math.PI * 2); ctx.fill();
      break;
    }
    case 'lamp': {
      ctx.translate(x, sy + Math.sin(o.t * 3) * 2);
      ctx.shadowColor = '#fff27a'; ctx.shadowBlur = 16;
      ctx.fillStyle = '#7a5a2a'; ctx.fillRect(-8, -9, 16, 18);
      ctx.fillStyle = '#ffe96a'; ctx.fillRect(-5, -6, 10, 9);
      ctx.shadowBlur = 0; ctx.fillStyle = '#3a2a14'; ctx.fillRect(-2, 4, 4, 4);
      break;
    }
    case 'rune': {
      ctx.translate(x, sy);
      const pulse = 1 + Math.sin(o.t * 4) * 0.08;
      ctx.scale(pulse, pulse);
      ctx.shadowColor = '#ffb040'; ctx.shadowBlur = 20;
      ctx.fillStyle = '#5a4630'; ctx.beginPath(); ctx.arc(0, 0, 14, 0, Math.PI * 2); ctx.fill();
      ctx.shadowBlur = 0; ctx.strokeStyle = '#ffd28a'; ctx.lineWidth = 2; ctx.stroke();
      ctx.fillStyle = '#ffd28a'; ctx.font = 'bold 11px Georgia'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.fillText('А.С.', 0, 1);
      break;
    }
    case 'stream': {
      const top = g.dir > 0 ? sy : sy - o.h;
      const w0 = wallAt(o.y), w1 = wallAt(o.y + g.dir * o.h);
      ctx.globalAlpha = 0.5;
      const gr = ctx.createLinearGradient(0, top, 0, top + o.h);
      gr.addColorStop(0, 'rgba(90,180,255,0)'); gr.addColorStop(0.5, 'rgba(110,200,255,.8)'); gr.addColorStop(1, 'rgba(90,180,255,0)');
      ctx.fillStyle = gr; ctx.fillRect(Math.min(w0.l, w1.l), top, Math.max(w0.r, w1.r) - Math.min(w0.l, w1.l), o.h);
      ctx.globalAlpha = 0.8; ctx.strokeStyle = '#bfe6ff'; ctx.lineWidth = 1.5;
      for (let i = 0; i < 7; i++) {
        const yy = top + ((i * 23 + g.t * 90) % o.h);
        ctx.beginPath(); ctx.moveTo(w0.l + 6, yy); ctx.quadraticCurveTo(W / 2, yy + 8, w0.r - 6, yy); ctx.stroke();
      }
      break;
    }
    case 'rock': {
      ctx.translate(x, sy); ctx.rotate(o.rot);
      ctx.fillStyle = '#6e6157'; ctx.strokeStyle = '#2a221c'; ctx.lineWidth = 2;
      ctx.beginPath();
      for (let i = 0; i < 7; i++) { const a = i / 7 * Math.PI * 2, rr = o.r * (0.8 + hash(i + o.r) * 0.35); i ? ctx.lineTo(Math.cos(a) * rr, Math.sin(a) * rr) : ctx.moveTo(Math.cos(a) * rr, Math.sin(a) * rr); }
      ctx.closePath(); ctx.fill(); ctx.stroke();
      break;
    }
    case 'bomb': {
      ctx.translate(x, sy);
      ctx.shadowColor = '#ff5a00'; ctx.shadowBlur = 18;
      ctx.fillStyle = '#2a120a'; ctx.beginPath(); ctx.arc(0, 0, o.r, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = '#ff7a20'; ctx.beginPath(); ctx.arc(-2, -2, o.r * 0.55, 0, Math.PI * 2); ctx.fill();
      break;
    }
    case 'ichthy': {
      const f = Math.sign(o.vx);
      ctx.translate(x, sy); ctx.scale(-f, 1);
      ctx.fillStyle = 'rgba(0,30,40,.35)'; ctx.beginPath(); ctx.ellipse(o.len / 2, 6, o.len * 0.6, 12, 0, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = '#3e6b6a';
      ctx.beginPath(); ctx.moveTo(-18, 0); ctx.quadraticCurveTo(10, -16, o.len, 0); ctx.quadraticCurveTo(10, 16, -18, 0); ctx.fill();
      ctx.beginPath(); ctx.moveTo(o.len - 4, 0); ctx.lineTo(o.len + 14, -12 + Math.sin(o.t * 10) * 4); ctx.lineTo(o.len + 14, 12 + Math.sin(o.t * 10) * 4); ctx.fill();
      ctx.beginPath(); ctx.moveTo(14, -6); ctx.lineTo(26, -20); ctx.lineTo(30, -6); ctx.fill();
      ctx.beginPath(); ctx.moveTo(14, 6); ctx.lineTo(26, 20); ctx.lineTo(30, 6); ctx.fill();
      ctx.fillStyle = '#ffde5a'; ctx.beginPath(); ctx.arc(-6, -3, 3.5, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = '#000'; ctx.beginPath(); ctx.arc(-6, -3, 1.6, 0, Math.PI * 2); ctx.fill();
      ctx.strokeStyle = '#e8e8d8'; ctx.lineWidth = 1;
      ctx.beginPath(); for (let i = 0; i < 4; i++) { ctx.moveTo(-16 + i * 3, 1); ctx.lineTo(-15 + i * 3, 4); } ctx.stroke();
      break;
    }
    case 'plesio': {
      ctx.translate(x, sy);
      ctx.fillStyle = 'rgba(0,30,40,.35)'; ctx.beginPath(); ctx.ellipse(0, 26, 34, 14, 0, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = '#4c5f3a'; ctx.beginPath(); ctx.ellipse(0, 26, 26, 12, 0, 0, Math.PI * 2); ctx.fill();
      ctx.strokeStyle = '#4c5f3a'; ctx.lineWidth = 8; ctx.lineCap = 'round';
      const hx = Math.sin(o.t * 2.4) * 10;
      ctx.beginPath(); ctx.moveTo(0, 20); ctx.quadraticCurveTo(hx * 1.5, 10, hx, 0); ctx.stroke();
      ctx.fillStyle = '#5c7046'; ctx.beginPath(); ctx.ellipse(hx, -2, 10, 7, 0, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = '#ff4a2a'; ctx.beginPath(); ctx.arc(hx - 4, -4, 1.8, 0, Math.PI * 2); ctx.arc(hx + 4, -4, 1.8, 0, Math.PI * 2); ctx.fill();
      ctx.strokeStyle = 'rgba(220,250,255,.4)'; ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.ellipse(0, 26, 32 + Math.sin(o.t * 3) * 3, 15, 0, 0, Math.PI * 2); ctx.stroke();
      break;
    }
    case 'ball': {
      ctx.translate(x, sy);
      const rr = o.r + Math.sin(o.t * 20) * 1.5;
      const gr = ctx.createRadialGradient(0, 0, 1, 0, 0, rr * 2.2);
      gr.addColorStop(0, '#ffffff'); gr.addColorStop(0.35, '#b8dcff'); gr.addColorStop(1, 'rgba(120,170,255,0)');
      ctx.fillStyle = gr; ctx.beginPath(); ctx.arc(0, 0, rr * 2.2, 0, Math.PI * 2); ctx.fill();
      ctx.strokeStyle = '#eaf6ff'; ctx.lineWidth = 1.2;
      for (let i = 0; i < 3; i++) {
        const a = o.t * 7 + i * 2.1; ctx.beginPath(); ctx.moveTo(0, 0);
        ctx.lineTo(Math.cos(a) * rr * 1.2, Math.sin(a) * rr * 1.2); ctx.lineTo(Math.cos(a + 0.4) * rr * 1.9, Math.sin(a + 0.4) * rr * 1.9); ctx.stroke();
      }
      break;
    }
    case 'shroom': {
      ctx.translate(x, sy);
      ctx.fillStyle = 'rgba(0,0,0,.35)'; ctx.beginPath(); ctx.ellipse(4, 6, o.r, o.r * 0.8, 0, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = `hsl(${o.hue},35%,72%)`;
      ctx.beginPath(); ctx.arc(0, 0, o.r, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = `hsl(${o.hue},30%,58%)`;
      ctx.beginPath(); ctx.arc(0, 0, o.r * 0.62, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = 'rgba(255,255,240,.6)';
      for (let i = 0; i < 5; i++) { const a = i * 1.3 + o.r; ctx.beginPath(); ctx.arc(Math.cos(a) * o.r * 0.75, Math.sin(a) * o.r * 0.75, 2.4, 0, Math.PI * 2); ctx.fill(); }
      break;
    }
    case 'mastodon': {
      const f = Math.sign(o.vx);
      ctx.translate(x, sy); ctx.scale(-f, 1);
      const leg = Math.sin(o.t * 8) * 3;
      ctx.fillStyle = 'rgba(0,0,0,.3)'; ctx.beginPath(); ctx.ellipse(26, 6, 40, 20, 0, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = '#6a4a32';
      ctx.beginPath(); ctx.ellipse(28, 0, 34, 20, 0, 0, Math.PI * 2); ctx.fill();
      ctx.beginPath(); ctx.arc(-4, -2, 15, 0, Math.PI * 2); ctx.fill();
      ctx.fillRect(10 + leg, 14, 8, 10); ctx.fillRect(40 - leg, 14, 8, 10);
      ctx.fillRect(10 - leg, -24, 8, 10); ctx.fillRect(40 + leg, -24, 8, 10);
      ctx.strokeStyle = '#6a4a32'; ctx.lineWidth = 5; ctx.lineCap = 'round';
      ctx.beginPath(); ctx.moveTo(-14, 0); ctx.quadraticCurveTo(-26, 6 + leg, -24, 14); ctx.stroke();
      ctx.strokeStyle = '#f0e6cc'; ctx.lineWidth = 3;
      ctx.beginPath(); ctx.moveTo(-12, -8); ctx.quadraticCurveTo(-30, -14, -28, -2);
      ctx.moveTo(-12, 6); ctx.quadraticCurveTo(-30, 12, -28, 0); ctx.stroke();
      ctx.fillStyle = '#000'; ctx.beginPath(); ctx.arc(-8, -7, 1.6, 0, Math.PI * 2); ctx.fill();
      break;
    }
  }
  ctx.restore();
}

function drawPerson(x, y, kind, lamp) {
  ctx.save(); ctx.translate(x, y);
  ctx.fillStyle = 'rgba(0,0,0,.35)'; ctx.beginPath(); ctx.ellipse(2, 4, 9, 6, 0, 0, Math.PI * 2); ctx.fill();
  const coat = kind === 'axel' ? '#3c5a8a' : kind === 'hans' ? '#6a5a3a' : '#5a3a2a';
  ctx.fillStyle = coat; ctx.beginPath(); ctx.ellipse(0, 2, 8, 9, 0, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = '#e8c39e'; ctx.beginPath(); ctx.arc(0, -7, 5.5, 0, Math.PI * 2); ctx.fill();
  if (kind === 'axel') { ctx.fillStyle = '#4a2a14'; ctx.beginPath(); ctx.arc(0, -9, 5.5, Math.PI, 0); ctx.fill(); }
  if (kind === 'hans') { ctx.fillStyle = '#e6c25a'; ctx.beginPath(); ctx.arc(0, -8, 6, Math.PI * 1.05, -0.05); ctx.fill(); ctx.fillRect(-4, -4, 8, 3); }
  if (kind === 'prof') {
    ctx.fillStyle = '#222'; ctx.fillRect(-6, -14, 12, 3); ctx.fillRect(-4, -18, 8, 5);
    ctx.strokeStyle = '#222'; ctx.lineWidth = 1; ctx.beginPath(); ctx.arc(-2, -7, 1.8, 0, Math.PI * 2); ctx.arc(2.5, -7, 1.8, 0, Math.PI * 2); ctx.stroke();
  }
  if (lamp) {
    ctx.shadowColor = '#fff1a0'; ctx.shadowBlur = 14;
    ctx.fillStyle = '#ffeb8a'; ctx.beginPath(); ctx.arc(8, 0, 3.5, 0, Math.PI * 2); ctx.fill();
  }
  ctx.restore();
}

function drawParty(camY) {
  const sy = g.y - camY, c = g.c;
  const blink = g.inv > 0 && Math.floor(g.t * 12) % 2 === 0;
  if (c.raft) {
    ctx.save(); ctx.translate(g.x, sy);
    const bob = Math.sin(g.t * 3) * 0.05; ctx.rotate(bob);
    ctx.fillStyle = 'rgba(0,0,0,.3)'; ctx.fillRect(-26, -20, 56, 50);
    ctx.fillStyle = '#7a5530';
    for (let i = 0; i < 6; i++) ctx.fillRect(-27 + i * 9, -24, 8, 48);
    ctx.strokeStyle = '#3a2614'; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(-28, -14); ctx.lineTo(27, -14); ctx.moveTo(-28, 14); ctx.lineTo(27, 14); ctx.stroke();
    ctx.restore();
    if (c.sea) { ctx.strokeStyle = 'rgba(220,250,255,.45)'; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(g.x, sy - g.dir * 28, 22, Math.PI * 0.15, Math.PI * 0.85); ctx.stroke(); }
    if (!blink) {
      drawPerson(g.x - 14, sy + 8, 'hans', false);
      drawPerson(g.x + 14, sy + 8, 'prof', false);
      drawPerson(g.x, sy - 8, 'axel', true);
    }
    return;
  }
  // спутники идут следом (по траектории)
  const h1 = g.hist[14] || g.x, h2 = g.hist[28] || g.x;
  drawPerson(h2, sy - g.dir * 50, 'hans', false);
  drawPerson(h1, sy - g.dir * 26, 'prof', false);
  ctx.strokeStyle = 'rgba(200,170,120,.5)'; ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(h2, sy - g.dir * 50); ctx.lineTo(h1, sy - g.dir * 26); ctx.lineTo(g.x, sy); ctx.stroke();
  if (!blink) drawPerson(g.x, sy, 'axel', true);
}

function drawDarkness(camY) {
  const c = g.c;
  let a = c.darkness;
  if (a <= 0) return;
  if (c.daylight > 0) a *= smooth(c.daylight * 0.3, c.daylight, g.dist);
  if (a <= 0.01) return;
  const sy = g.y - camY + g.dir * 45; // лампа светит вперёд, по ходу движения
  const radius = 70 + 170 * (g.lamp / 100) + Math.sin(g.t * 9) * 3;
  dctx.globalCompositeOperation = 'source-over';
  dctx.clearRect(0, 0, W, H);
  dctx.fillStyle = c.lava ? `rgba(30,6,0,${a})` : `rgba(4,3,2,${a})`;
  dctx.fillRect(0, 0, W, H);
  dctx.globalCompositeOperation = 'destination-out';
  const gr = dctx.createRadialGradient(g.x, sy, 8, g.x, sy, radius);
  gr.addColorStop(0, 'rgba(0,0,0,1)'); gr.addColorStop(0.55, 'rgba(0,0,0,.85)'); gr.addColorStop(1, 'rgba(0,0,0,0)');
  dctx.fillStyle = gr; dctx.beginPath(); dctx.arc(g.x, sy, radius, 0, Math.PI * 2); dctx.fill();
  // светящиеся предметы видны в темноте
  for (const o of g.objs) {
    if (o.type === 'bomb' || o.type === 'gem' || o.type === 'rune' || o.type === 'lamp' || o.type === 'water' || o.type === 'stream') {
      const r = o.type === 'stream' ? 70 : o.type === 'bomb' ? 34 : 22;
      const oy = o.type === 'stream' ? o.y - camY + g.dir * o.h / 2 : o.y - camY;
      const ox = o.type === 'stream' ? W / 2 : o.x;
      const g2 = dctx.createRadialGradient(ox, oy, 1, ox, oy, r);
      g2.addColorStop(0, 'rgba(0,0,0,.8)'); g2.addColorStop(1, 'rgba(0,0,0,0)');
      dctx.fillStyle = g2; dctx.beginPath(); dctx.arc(ox, oy, r, 0, Math.PI * 2); dctx.fill();
    }
  }
  if (c.lava) {
    const lg = dctx.createLinearGradient(0, H * 0.7, 0, H);
    lg.addColorStop(0, 'rgba(0,0,0,0)'); lg.addColorStop(1, 'rgba(0,0,0,1)');
    dctx.fillStyle = lg; dctx.fillRect(0, H * 0.7, W, H * 0.3);
  }
  ctx.drawImage(dark, 0, 0, W, H);
}

function bar(x, y, w, h, v, color, icon) {
  ctx.fillStyle = 'rgba(0,0,0,.5)'; ctx.fillRect(x, y, w, h);
  ctx.fillStyle = color; ctx.fillRect(x + 1, y + 1, (w - 2) * clamp(v / 100, 0, 1), h - 2);
  ctx.strokeStyle = 'rgba(255,220,170,.35)'; ctx.strokeRect(x + 0.5, y + 0.5, w - 1, h - 1);
  ctx.font = '13px sans-serif'; ctx.textAlign = 'right'; ctx.textBaseline = 'middle'; ctx.fillStyle = '#fff';
  ctx.fillText(icon, x - 3, y + h / 2 + 1);
}

function drawHud() {
  const c = g.c;
  ctx.fillStyle = 'rgba(10,6,3,.55)'; ctx.fillRect(0, 0, W, 64);
  ctx.textBaseline = 'middle';
  // жизни
  ctx.font = '17px sans-serif'; ctx.textAlign = 'left';
  for (let i = 0; i < 3; i++) { ctx.globalAlpha = i < g.hearts ? 1 : 0.25; ctx.fillText('❤️', 8 + i * 22, 16); }
  ctx.globalAlpha = 1;
  const lowWater = g.water < 25 && Math.floor(g.t * 4) % 2 === 0;
  bar(98, 8, 92, 12, g.water, lowWater ? '#ff6a5a' : '#4fa8e8', '💧');
  if (c.darkness > 0 && c.lampDrain > 0) bar(98, 26, 92, 12, g.lamp, '#ffd84a', '🏮');
  ctx.textAlign = 'right'; ctx.fillStyle = '#ffd28a'; ctx.font = 'bold 15px Georgia';
  ctx.fillText(Math.floor(g.score) + ' ✦', W - 62, 14);
  ctx.font = '12px Georgia'; ctx.fillStyle = '#e6cfa8';
  ctx.fillText((g.ci < 4 ? 'глубина ' : 'до поверхности ') + depthKm().toFixed(1) + ' км', W - 62, 32);
  ctx.textAlign = 'left'; ctx.font = 'italic 12px Georgia'; ctx.fillStyle = '#c9ab83';
  ctx.fillText(c.roman + '. ' + c.name + (g.runeGot ? '  ᚨ' : ''), 8, 50);
  // прогресс главы
  ctx.fillStyle = 'rgba(255,255,255,.12)'; ctx.fillRect(0, 62, W, 2);
  ctx.fillStyle = '#ffb45e'; ctx.fillRect(0, 62, W * clamp(g.dist / c.len, 0, 1), 2);
  // предупреждения
  for (const wn of g.warns) {
    if (Math.floor(wn.t * 10) % 2) continue;
    const y = g.dir > 0 ? 80 : H - 24;
    ctx.fillStyle = c.lava ? '#ff6a2a' : '#ffd28a'; ctx.font = 'bold 20px sans-serif'; ctx.textAlign = 'center';
    ctx.fillText(g.dir > 0 ? '▼' : '▲', wn.x, y);
  }
  if (g.msg) {
    ctx.globalAlpha = Math.min(1, g.msg.t * 2);
    ctx.font = 'bold 18px Georgia'; ctx.textAlign = 'center';
    ctx.lineWidth = 4; ctx.strokeStyle = 'rgba(0,0,0,.7)';
    const my = g.dir > 0 ? H * 0.62 : H * 0.42;
    ctx.strokeText(g.msg.text, W / 2, my); ctx.fillStyle = g.msg.color; ctx.fillText(g.msg.text, W / 2, my);
    ctx.globalAlpha = 1;
  }
}

function render(noHud) {
  ctx.setTransform(S * DPR, 0, 0, S * DPR, 0, 0);
  if (!g) { ctx.fillStyle = '#120c08'; ctx.fillRect(0, 0, W, H); return; }
  ctx.save();
  if (g.shake > 0) ctx.translate(rand(-4, 4) * g.shake * 3, rand(-4, 4) * g.shake * 3);
  const camY = cameraY();
  drawBackground(camY);
  for (const d of g.decor) drawDecor(d, d.y - camY);
  for (const o of g.objs) if (o.type === 'stream') drawObj(o, o.y - camY);
  drawWalls(camY);
  for (const o of g.objs) if (o.type !== 'stream') drawObj(o, o.y - camY);
  drawParty(camY);
  for (const pt of g.parts) {
    ctx.globalAlpha = clamp(pt.life / pt.max, 0, 1); ctx.fillStyle = pt.color;
    ctx.fillRect(pt.x - pt.s / 2, pt.y - camY - pt.s / 2, pt.s, pt.s);
  }
  ctx.globalAlpha = 1;
  drawDarkness(camY);
  ctx.restore();
  if (g.flash > 0) { ctx.fillStyle = `rgba(255,60,30,${g.flash})`; ctx.fillRect(0, 0, W, H); }
  if (!noHud) drawHud();
}

// ---------- Экраны ----------
const $ = id => document.getElementById(id);
const screens = ['menu', 'chapters', 'help', 'story', 'pause', 'over'];
function show(id) {
  for (const s of screens) $(s).classList.toggle('hidden', s !== id);
  pauseBtn.classList.toggle('hidden', id !== null);
}

function updateMenu() {
  $('bestLine').textContent = save.best > 0 ? `Рекорд: ${save.best} ✦  ·  Руны: ${save.runes.length}/5` + (save.won ? '  ·  Стромболи достигнут!' : '') : '';
  $('btnSound').textContent = 'Звук: ' + (save.sound ? 'вкл' : 'выкл');
  const list = $('chapterList'); list.innerHTML = '';
  CH.forEach((c, i) => {
    const b = document.createElement('button');
    b.className = 'btn chap';
    b.disabled = i + 1 > save.unlocked;
    b.innerHTML = `<span class="num">${c.roman}</span><span>${b.disabled ? '🔒 ' : ''}${c.name}</span><span class="rune">${save.runes.includes(i) ? 'ᚨ' : ''}</span>`;
    b.onclick = () => startChapter(i, false);
    list.appendChild(b);
  });
}

function toMenu() { state = 'menu'; updateMenu(); show('menu'); }

function startChapter(i, keepScore) {
  newGame(i, keepScore);
  state = 'story';
  const c = CH[i];
  $('storyKicker').textContent = 'Глава ' + c.roman;
  $('storyTitle').textContent = c.name;
  $('storyText').innerHTML = c.text.map(t => `<p>${t}</p>`).join('');
  $('storyBtn').textContent = 'В путь';
  $('storyBtn').onclick = () => { state = 'play'; last = performance.now(); show(null); };
  show('story');
}

function chapterDone() {
  const next = g.ci + 1;
  save.best = Math.max(save.best, Math.floor(g.score));
  if (next < CH.length) {
    save.unlocked = Math.max(save.unlocked, next + 1); persist();
    const bonus = g.hearts * 50; g.score += bonus;
    startChapter(next, true);
    $('storyText').insertAdjacentHTML('afterbegin', `<p style="color:#8fd88f">Глава пройдена! Бонус за жизни: +${bonus} ✦</p>`);
  } else victory();
}

function victory() {
  state = 'story';
  g.score += g.hearts * 50 + 500;
  const total = Math.floor(g.score);
  const allRunes = save.runes.length >= 5;
  save.best = Math.max(save.best, total); save.won = true; persist();
  $('storyKicker').textContent = 'Эпилог';
  $('storyTitle').textContent = 'Стромболи!';
  $('storyText').innerHTML = [
    'Вулкан выбросил плот к солнцу. Вокруг — оливковые рощи, виноградники и синее море. Мальчик-пастух объясняет: это остров Стромболи, Италия!',
    'Вы вошли в недра Земли в Исландии, а вышли за тысячи километров — в Средиземном море. В Гамбурге экспедицию встречают как героев.',
    allRunes ? 'Все пять рун Сакнуссема собраны — вы прошли его путь целиком. Профессор Лиденброк гордится вами!' : `Рун Сакнуссема найдено: ${save.runes.length} из 5. Найдите все, чтобы пройти его путь целиком.`,
    `<b>Итог экспедиции: ${total} ✦</b>`,
  ].map(t => `<p>${t}</p>`).join('');
  $('storyBtn').textContent = 'В меню';
  $('storyBtn').onclick = toMenu;
  show('story');
}

function gameOver() {
  state = 'over';
  save.best = Math.max(save.best, Math.floor(g.score)); persist();
  $('overText').textContent = `Глава «${g.c.name}». Пройдено ${Math.floor(g.dist / g.c.len * 100)}%, очки: ${Math.floor(g.score)} ✦`;
  show('over');
}

function pauseGame() { if (state !== 'play') return; state = 'pause'; show('pause'); }
function resumeGame() { state = 'play'; last = performance.now(); show(null); }

$('btnNew').onclick = () => { audio(); startChapter(0, false); };
$('btnChapters').onclick = () => { updateMenu(); show('chapters'); };
$('btnHelp').onclick = () => show('help');
$('btnSound').onclick = () => { save.sound = !save.sound; persist(); updateMenu(); if (save.sound) sfx.gem(); };
document.querySelectorAll('[data-back]').forEach(b => b.onclick = toMenu);
$('btnResume').onclick = resumeGame;
$('btnRestart').onclick = () => startChapter(g.ci, false);
$('btnToMenu').onclick = toMenu;
$('btnRetry').onclick = () => startChapter(g.ci, false);
$('btnOverMenu').onclick = toMenu;
pauseBtn.onclick = pauseGame;
document.addEventListener('visibilitychange', () => { if (document.hidden) pauseGame(); });

// Кнопка «Назад» Android: true — обработано в игре, false — можно закрыть приложение
window.czBack = () => {
  if (state === 'play') { pauseGame(); return true; }
  if (state === 'pause') { resumeGame(); return true; }
  if (state === 'menu') return false;
  toMenu(); return true;
};

// ---------- Главный цикл ----------
let last = performance.now();
function frame(now) {
  const dt = Math.min(0.05, (now - last) / 1000); last = now;
  if (state === 'play') update(dt);
  if (state === 'menu' || !g) renderMenuBg(now / 1000);
  else render();
  requestAnimationFrame(frame);
}

// фон меню — медленный спуск по шахте
let menuG = null;
function renderMenuBg(t) {
  const saved = g;
  if (!menuG) { newGame(0, false); menuG = g; }
  g = menuG;
  g.t = t; g.y = 1200 + t * 40; g.dist = 2000; g.lamp = 70;
  render(true);
  g = saved;
}

toMenu();
requestAnimationFrame(frame);
})();
