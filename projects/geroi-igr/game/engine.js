'use strict';
/* ===== Движок: персонажи, сохранения, ввод, физика, звук ===== */

const CHARS = [
  {
    id: 'david', name: 'Давид', title: 'Самый высокий', emoji: '🦒', height: 1.3,
    skin: 0xe8b58f, shirt: 0x2b6cff, pants: 0x1d2a44, hair: 0x2a1a0e, hairStyle: 'short',
    perk: 'Длинные руки: ловит, ищет и собирает на 40% дальше. Прыгает выше всех.',
    base: { speed: 5.6, jump: 9.4, stamina: 5, hp: 3, reach: 1.4, power: 1, time: 1, luck: 1 }
  },
  {
    id: 'muhamad', name: 'Мухамад', title: 'Самый быстрый', emoji: '⚡', height: 1.08,
    skin: 0xc68e64, shirt: 0x19b36b, pants: 0x333333, hair: 0x111111, hairStyle: 'curly',
    perk: 'Быстрые ноги: бегает на 15% быстрее и дольше не устаёт.',
    base: { speed: 6.5, jump: 8.6, stamina: 6, hp: 3, reach: 1, power: 1, time: 1, luck: 1 }
  },
  {
    id: 'mark', name: 'Марк', title: 'Самый умный', emoji: '🧠', height: 1.05,
    skin: 0xf1c8a5, shirt: 0xffb02e, pants: 0x3b4f7a, hair: 0xc08a3e, hairStyle: 'side', glasses: true,
    perk: 'Умная голова: +20% времени на каждом уровне.',
    base: { speed: 5.8, jump: 8.6, stamina: 5, hp: 3, reach: 1.1, power: 1, time: 1.2, luck: 1 }
  },
  {
    id: 'mustafo', name: 'Мустафо', title: 'Самый сильный', emoji: '💪', height: 1.12,
    skin: 0xd29c72, shirt: 0xe23d3d, pants: 0x2d2d2d, hair: 0x1a120b, hairStyle: 'buzz',
    perk: 'Силач: +1 жизнь, удар отбрасывает врагов и мяч вдвое сильнее.',
    base: { speed: 5.7, jump: 8.5, stamina: 5, hp: 4, reach: 1.1, power: 1.9, time: 1, luck: 1 }
  },
  {
    id: 'hero', name: 'Новичок', title: 'Твой герой', emoji: '⭐', height: 1.0, custom: true,
    skin: 0xf6d6bd, shirt: 0x8e44ff, pants: 0x222244, hair: 0x7a4b23, hairStyle: 'curly',
    perk: 'Везунчик: +30% монет. Имя можно поменять!',
    base: { speed: 5.8, jump: 8.8, stamina: 5, hp: 3, reach: 1.1, power: 1.1, time: 1, luck: 1.3 }
  }
];
const charById = id => CHARS.find(c => c.id === id) || CHARS[0];

const UPGRADES = [
  { id: 'speed', name: 'Скорость', emoji: '⚡', max: 10, desc: '+4% к бегу' },
  { id: 'jump', name: 'Прыжок', emoji: '🦘', max: 10, desc: '+3% к высоте прыжка' },
  { id: 'stamina', name: 'Выносливость', emoji: '💨', max: 10, desc: '+15% к рывку' },
  { id: 'hp', name: 'Здоровье', emoji: '❤️', max: 4, desc: '+1 жизнь' },
  { id: 'magnet', name: 'Магнит', emoji: '🧲', max: 8, desc: 'монеты притягиваются дальше' },
  { id: 'power', name: 'Сила', emoji: '👊', max: 8, desc: '+10% к удару' }
];
const upgradeCost = (u, lvl) => Math.round((u.id === 'hp' ? 120 : 40) * Math.pow(lvl + 1, 1.45));

// ---------- Сохранение ----------
const SAVE_KEY = 'geroi_igr_save_v1';
let save;
function defaultSave() {
  const s = { coins: 60, chosen: 'david', heroName: 'Новичок', sound: true, music: true, chars: {}, done: {} };
  CHARS.forEach(c => { s.chars[c.id] = { xp: 0, level: 1, up: { speed: 0, jump: 0, stamina: 0, hp: 0, magnet: 0, power: 0 } }; });
  return s;
}
function loadSave() {
  try {
    const raw = localStorage.getItem(SAVE_KEY);
    if (raw) {
      const d = JSON.parse(raw), def = defaultSave();
      save = Object.assign(def, d);
      CHARS.forEach(c => {
        save.chars[c.id] = Object.assign(def.chars[c.id], d.chars && d.chars[c.id]);
        save.chars[c.id].up = Object.assign({ speed: 0, jump: 0, stamina: 0, hp: 0, magnet: 0, power: 0 }, save.chars[c.id].up);
      });
      return;
    }
  } catch (e) { /* повреждённое сохранение — начнём заново */ }
  save = defaultSave();
}
function writeSave() { try { localStorage.setItem(SAVE_KEY, JSON.stringify(save)); } catch (e) { } }
loadSave();

const xpNeed = lvl => 80 + lvl * 60;
const charName = c => (c.custom ? (save.heroName || c.name) : c.name);

function charStats(id) {
  const c = charById(id), s = save.chars[id], u = s.up, lv = s.level - 1;
  const m = 1 + 0.015 * lv;
  return {
    speed: c.base.speed * m * (1 + 0.04 * u.speed),
    jump: c.base.jump * (1 + 0.008 * lv) * (1 + 0.03 * u.jump),
    stamina: c.base.stamina * (1 + 0.15 * u.stamina),
    hp: c.base.hp + u.hp,
    reach: c.base.reach,
    magnet: 1.2 + 0.45 * u.magnet,
    power: c.base.power * (1 + 0.1 * u.power + 0.01 * lv),
    time: c.base.time,
    luck: c.base.luck
  };
}

function kidOptsFor(id, costume) {
  const c = charById(id), lvl = save.chars[id].level;
  return {
    height: c.height, skin: c.skin, shirt: c.shirt, pants: c.pants, hair: c.hair, hairStyle: c.hairStyle,
    glasses: c.glasses, costume, hat: lvl >= 8 ? 'crown' : lvl >= 3 ? 'cap' : null, hatColor: c.shirt
  };
}

// ---------- Звук ----------
let actx = null, musicTimer = null, musicStep = 0, musicTheme = null;
function audio() {
  if (!actx) { try { actx = new (window.AudioContext || window.webkitAudioContext)(); } catch (e) { } }
  if (actx && actx.state === 'suspended') actx.resume();
  return actx;
}
function beep(freq, dur, type, vol, slide) {
  if (!save.sound) return;
  const a = audio(); if (!a) return;
  const o = a.createOscillator(), g = a.createGain();
  o.type = type || 'square';
  o.frequency.setValueAtTime(freq, a.currentTime);
  if (slide) o.frequency.exponentialRampToValueAtTime(Math.max(30, slide), a.currentTime + dur);
  g.gain.setValueAtTime(vol || 0.08, a.currentTime);
  g.gain.exponentialRampToValueAtTime(0.0001, a.currentTime + dur);
  o.connect(g); g.connect(a.destination);
  o.start(); o.stop(a.currentTime + dur + 0.02);
}
const SFX = {
  coin: () => { beep(988, 0.07, 'square', 0.05); setTimeout(() => beep(1319, 0.12, 'square', 0.05), 60); },
  jump: () => beep(300, 0.18, 'square', 0.04, 700),
  hit: () => beep(200, 0.3, 'sawtooth', 0.09, 60),
  punch: () => beep(140, 0.12, 'triangle', 0.15, 60),
  good: () => [523, 659, 784].forEach((f, i) => setTimeout(() => beep(f, 0.12, 'triangle', 0.08), i * 80)),
  bad: () => beep(180, 0.25, 'square', 0.06, 110),
  win: () => [523, 659, 784, 1047, 784, 1047].forEach((f, i) => setTimeout(() => beep(f, 0.18, 'triangle', 0.09), i * 120)),
  lose: () => [392, 330, 262, 196].forEach((f, i) => setTimeout(() => beep(f, 0.25, 'sawtooth', 0.06), i * 180)),
  web: () => beep(1200, 0.25, 'sine', 0.06, 300),
  click: () => beep(660, 0.05, 'square', 0.04),
  giggle: () => [900, 1100, 950, 1200].forEach((f, i) => setTimeout(() => beep(f, 0.06, 'sine', 0.035), i * 70)),
  levelup: () => [523, 659, 784, 1047, 1319].forEach((f, i) => setTimeout(() => beep(f, 0.15, 'square', 0.06), i * 90))
};

// Простая фоновая музыка-чиптюн
const THEMES = {
  menu: { bpm: 220, bass: [48, 48, 55, 55, 53, 53, 50, 55], mel: [72, 0, 76, 79, 77, 76, 74, 0, 72, 74, 76, 0, 79, 77, 76, 74] },
  play: { bpm: 260, bass: [45, 45, 52, 52, 50, 50, 52, 52], mel: [69, 72, 76, 72, 74, 77, 81, 77, 76, 72, 69, 72, 71, 74, 76, 0] },
  spooky: { bpm: 180, bass: [40, 40, 43, 43, 46, 46, 43, 43], mel: [64, 0, 67, 0, 70, 0, 67, 66, 64, 0, 63, 0, 64, 0, 0, 0] },
  space: { bpm: 200, bass: [41, 41, 44, 44, 46, 46, 44, 39], mel: [77, 0, 80, 0, 82, 80, 77, 0, 75, 0, 77, 0, 73, 0, 0, 0] }
};
const midi = n => 440 * Math.pow(2, (n - 69) / 12);
function playMusic(name) {
  if (musicTheme === name && musicTimer) return;
  stopMusic();
  musicTheme = name;
  if (!save.music || !name) return;
  const th = THEMES[name];
  musicStep = 0;
  musicTimer = setInterval(() => {
    if (!save.music || document.hidden) return;
    const a = audio(); if (!a) return;
    const n = th.mel[musicStep % th.mel.length];
    if (n) tone(midi(n), 0.16, 'square', 0.022);
    if (musicStep % 2 === 0) tone(midi(th.bass[(musicStep / 2) % th.bass.length]), 0.25, 'triangle', 0.05);
    musicStep++;
  }, 60000 / th.bpm);
}
function tone(f, d, type, v) {
  const a = actx; if (!a) return;
  const o = a.createOscillator(), g = a.createGain();
  o.type = type; o.frequency.value = f;
  g.gain.setValueAtTime(v, a.currentTime); g.gain.exponentialRampToValueAtTime(0.0001, a.currentTime + d);
  o.connect(g); g.connect(a.destination); o.start(); o.stop(a.currentTime + d + 0.02);
}
function stopMusic() { if (musicTimer) clearInterval(musicTimer); musicTimer = null; }

// ---------- Ввод ----------
const input = { x: 0, z: 0, jump: false, action: false, actionHeld: false, sprint: false, keys: {} };
function setupInput() {
  const joy = document.getElementById('joy'), knob = document.getElementById('joyKnob'), zone = document.getElementById('joyZone');
  let jid = null, cx = 0, cy = 0;
  const R = 55;
  zone.addEventListener('touchstart', e => {
    e.preventDefault();
    const t = e.changedTouches[0]; jid = t.identifier; cx = t.clientX; cy = t.clientY;
    joy.style.left = (cx - 70) + 'px'; joy.style.top = (cy - 70) + 'px'; joy.classList.add('on');
    knob.style.transform = 'translate(0px,0px)';
  }, { passive: false });
  zone.addEventListener('touchmove', e => {
    e.preventDefault();
    for (const t of e.changedTouches) if (t.identifier === jid) {
      let dx = t.clientX - cx, dy = t.clientY - cy;
      const d = Math.hypot(dx, dy);
      if (d > R) { dx *= R / d; dy *= R / d; }
      knob.style.transform = `translate(${dx}px,${dy}px)`;
      input.x = dx / R; input.z = dy / R;
    }
  }, { passive: false });
  const end = e => {
    for (const t of e.changedTouches) if (t.identifier === jid) {
      jid = null; input.x = input.z = 0; joy.classList.remove('on');
    }
  };
  zone.addEventListener('touchend', end); zone.addEventListener('touchcancel', end);

  const bindBtn = (id, down, up) => {
    const b = document.getElementById(id);
    const d = e => { e.preventDefault(); audio(); b.classList.add('pressed'); down(); };
    const u = e => { e.preventDefault(); b.classList.remove('pressed'); if (up) up(); };
    b.addEventListener('touchstart', d, { passive: false });
    b.addEventListener('touchend', u, { passive: false });
    b.addEventListener('touchcancel', u, { passive: false });
    b.addEventListener('mousedown', d); b.addEventListener('mouseup', u); b.addEventListener('mouseleave', u);
  };
  bindBtn('btnJump', () => { input.jump = true; });
  bindBtn('btnAction', () => { input.action = true; input.actionHeld = true; }, () => { input.actionHeld = false; });
  bindBtn('btnSprint', () => { input.sprintBtn = true; }, () => { input.sprintBtn = false; });

  window.addEventListener('keydown', e => {
    input.keys[e.code] = true;
    if (e.code === 'Space') { input.jump = true; e.preventDefault(); }
    if (e.code === 'KeyE' || e.code === 'KeyF' || e.code === 'Enter') { if (!e.repeat) input.action = true; input.actionHeld = true; }
    if (e.code === 'Escape' || e.code === 'KeyP') { if (typeof togglePause === 'function') togglePause(); }
  });
  window.addEventListener('keyup', e => {
    input.keys[e.code] = false;
    if (e.code === 'KeyE' || e.code === 'KeyF' || e.code === 'Enter') input.actionHeld = false;
  });
}
function readKeys() {
  const k = input.keys;
  let x = 0, z = 0;
  if (k.KeyA || k.ArrowLeft) x -= 1;
  if (k.KeyD || k.ArrowRight) x += 1;
  if (k.KeyW || k.ArrowUp) z -= 1;
  if (k.KeyS || k.ArrowDown) z += 1;
  if (x || z) { const d = Math.hypot(x, z); input.x = x / d; input.z = z / d; input.kb = true; }
  else if (input.kb) { input.x = input.z = 0; input.kb = false; }
  input.sprint = !!(input.sprintBtn || k.ShiftLeft || k.ShiftRight);
}

// ---------- Физика ----------
const GRAV = 24, STEP = 0.4;

function addCollider(L, minX, maxX, minZ, maxZ, minY, maxY, extra) {
  const c = Object.assign({ minX, maxX, minZ, maxZ, minY, maxY, dx: 0, dy: 0, dz: 0 }, extra || {});
  L.colliders.push(c);
  return c;
}
// Блок с коллайдером: центр x,z; размеры w,d; низ y0, высота h
function addBlock(L, x, z, w, d, h, color, y0, opts) {
  y0 = y0 || 0;
  const m = mesh(G_BOX, typeof color === 'object' ? color : mat(color), x, y0 + h / 2, z);
  m.scale.set(w, h, d);
  L.scene.add(m);
  const c = addCollider(L, x - w / 2, x + w / 2, z - d / 2, z + d / 2, y0, y0 + h, Object.assign({ mesh: m }, opts || {}));
  return c;
}
function syncColliderMesh(c) {
  const w = c.maxX - c.minX, h = c.maxY - c.minY, d = c.maxZ - c.minZ;
  c.mesh.position.set((c.minX + c.maxX) / 2, c.minY + h / 2, (c.minZ + c.maxZ) / 2);
  c.mesh.scale.set(w, h, d);
}
function moveCollider(c, dx, dy, dz) {
  c.minX += dx; c.maxX += dx; c.minY += dy; c.maxY += dy; c.minZ += dz; c.maxZ += dz;
  c.dx += dx; c.dy += dy; c.dz += dz;
  if (c.mesh) {
    if (c.meshOffset) c.mesh.position.add(new THREE.Vector3(dx, dy, dz));
    else syncColliderMesh(c);
  }
}

// e: {pos, vel, r, h, onGround, ground}
function moveEntity(e, dt, L) {
  // ехать вместе с движущейся платформой
  if (e.ground && e.onGround) { e.pos.x += e.ground.dx; e.pos.y += e.ground.dy; e.pos.z += e.ground.dz; }
  e.pos.x += e.vel.x * dt;
  e.pos.z += e.vel.z * dt;
  const cols = L.colliders;
  for (let i = 0; i < cols.length; i++) {
    const c = cols[i];
    if (c.off || c.noSide) continue;
    if (e.pos.y > c.maxY - STEP || e.pos.y + e.h < c.minY) continue;
    const cx = clamp(e.pos.x, c.minX, c.maxX), cz = clamp(e.pos.z, c.minZ, c.maxZ);
    const dx = e.pos.x - cx, dz = e.pos.z - cz, d2 = dx * dx + dz * dz;
    if (d2 < e.r * e.r) {
      if (d2 > 1e-8) {
        const d = Math.sqrt(d2), k = (e.r - d) / d;
        e.pos.x += dx * k; e.pos.z += dz * k;
      } else {
        const l = e.pos.x - c.minX, r = c.maxX - e.pos.x, b = e.pos.z - c.minZ, f = c.maxZ - e.pos.z, m = Math.min(l, r, b, f);
        if (m === l) e.pos.x = c.minX - e.r; else if (m === r) e.pos.x = c.maxX + e.r;
        else if (m === b) e.pos.z = c.minZ - e.r; else e.pos.z = c.maxZ + e.r;
      }
      e.bumped = true;
    }
  }
  const prevY = e.pos.y;
  e.vel.y -= GRAV * dt;
  if (e.vel.y < -40) e.vel.y = -40;
  e.pos.y += e.vel.y * dt;
  // земля
  let gy = L.floor ? 0 : -Infinity, gc = null;
  const m = e.r * 0.55;
  for (let i = 0; i < cols.length; i++) {
    const c = cols[i];
    if (c.off) continue;
    if (e.pos.x < c.minX - m || e.pos.x > c.maxX + m || e.pos.z < c.minZ - m || e.pos.z > c.maxZ + m) continue;
    if (prevY >= c.maxY - STEP - 0.05 && c.maxY > gy) { gy = c.maxY; gc = c; }
    // потолок
    if (e.vel.y > 0 && prevY + e.h <= c.minY + 0.01 && e.pos.y + e.h > c.minY) { e.pos.y = c.minY - e.h; e.vel.y = 0; }
  }
  e.onGround = false;
  if (e.pos.y <= gy) {
    e.pos.y = gy; if (e.vel.y < 0) e.vel.y = 0;
    e.onGround = true; e.ground = gc;
  } else if (e.pos.y - gy < 0.08 && e.vel.y <= 0) {
    e.pos.y = gy; e.vel.y = 0; e.onGround = true; e.ground = gc;
  } else e.ground = null;
}

function resetColliderDeltas(L) { for (const c of L.colliders) { c.dx = c.dy = c.dz = 0; } }

// Свободное место (не внутри коллайдеров)
function freeSpot(L, x, z, r) {
  for (const c of L.colliders) {
    if (c.maxY < 0.3 || c.off) continue;
    if (x > c.minX - r && x < c.maxX + r && z > c.minZ - r && z < c.maxZ + r) return false;
  }
  return true;
}
function randomFreeSpot(L, half, r, avoid) {
  for (let i = 0; i < 200; i++) {
    const x = rand(-half, half), z = rand(-half, half);
    if (!freeSpot(L, x, z, r)) continue;
    if (avoid && avoid.some(a => Math.hypot(a.x - x, a.z - z) < a.r)) continue;
    return { x, z };
  }
  return { x: 0, z: 0 };
}
