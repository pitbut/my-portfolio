'use strict';
/* ===== Ядро игры: рендер, игрок, уровни, экраны ===== */

const canvas = document.getElementById('c');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' });
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.6));
renderer.shadowMap.enabled = save.shadows !== false;
renderer.shadowMap.type = THREE.PCFShadowMap;
const camera = new THREE.PerspectiveCamera(55, 1, 0.1, 500);
const clock = new THREE.Clock();
const $ = s => document.querySelector(s);

let scene = null;          // текущая сцена
let mode = 'menu';         // menu | game
let L = null;              // текущий уровень
let P = null;              // игрок
let G = null;              // состояние забега
let menuKids = [];
let selIndex = Math.max(0, CHARS.findIndex(c => c.id === save.chosen));
let pendingLevel = null;
let menuLookY = 1.3;

function resize() {
  const w = window.innerWidth, h = window.innerHeight;
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.fov = w < h ? 68 : 55;
  camera.updateProjectionMatrix();
}
window.addEventListener('resize', resize);

function disposeScene(sc) {
  if (!sc) return;
  sc.traverse(o => {
    if (o.geometry && o.geometry !== G_BOX && o.geometry !== G_SPH && o.geometry !== G_CYL) o.geometry.dispose();
    if (o.material && o.material.map) o.material.map.dispose();
    if (o.isSprite) o.material.dispose();
  });
}

function baseScene(sky, fog) {
  const sc = new THREE.Scene();
  sc.background = new THREE.Color(sky || 0x87ceeb);
  if (fog) sc.fog = new THREE.Fog(fog[0], fog[1], fog[2]);
  const hemi = new THREE.HemisphereLight(0xffffff, 0x556644, 0.85);
  sc.add(hemi);
  const sun = new THREE.DirectionalLight(0xffffff, 1.0);
  sun.position.set(10, 22, 8);
  sun.castShadow = true;
  sun.shadow.mapSize.set(1024, 1024);
  const sh = sun.shadow.camera; sh.left = -22; sh.right = 22; sh.top = 22; sh.bottom = -22; sh.near = 1; sh.far = 70;
  sun.shadow.bias = -0.0008;
  sc.add(sun); sc.add(sun.target);
  sc.userData = { sun, hemi };
  return sc;
}

// ================= МЕНЮ (3D-витрина героев) =================
function buildMenuScene() {
  disposeScene(scene);
  scene = baseScene(0x9bd7ff);
  const ground = mesh(new THREE.CircleGeometry(30, 40), mat(0x6cc56c), 0, 0, 0, false);
  ground.rotation.x = -Math.PI / 2; scene.add(ground);
  const stage = mesh(new THREE.CylinderGeometry(7, 7.4, 0.4, 40), mat(0xffd166), 0, 0.2, 0); scene.add(stage);
  const stage2 = mesh(new THREE.CylinderGeometry(5.5, 5.5, 0.12, 40), mat(0xff8fab), 0, 0.46, 0); scene.add(stage2);
  for (let i = 0; i < 14; i++) {
    const a = i / 14 * Math.PI * 2;
    scene.add(makeTree(Math.cos(a) * rand(14, 22), Math.sin(a) * rand(14, 22) - 4, rand(0.9, 1.4)));
  }
  // шарики
  for (let i = 0; i < 10; i++) {
    const b = mesh(G_SPH, mat(pick(KID_COLORS)), rand(-12, 12), rand(5, 10), rand(-14, -6)); b.scale.set(0.5, 0.6, 0.5);
    b.userData.float = rand(0, 6); scene.add(b);
  }
  menuKids = CHARS.map((c, i) => {
    const k = makeKid(kidOptsFor(c.id));
    k.position.set((i - 2) * 1.9, 0.52, 0);
    const lab = textSprite(charName(c), '#fff', 'rgba(40,40,90,0.7)', 1.8);
    lab.position.y = k.userData.topY + 0.25; k.add(lab);
    k.userData.label = lab;
    scene.add(k);
    return k;
  });
  camera.position.set(0, 3.2, 9);
  camera.lookAt(0, 1.2, 0);
}

function updateMenu(dt) {
  const t = performance.now() / 1000;
  menuKids.forEach((k, i) => {
    const sel = i === selIndex;
    const tx = (i - 2) * 1.9, tz = sel ? 1.6 : 0;
    k.position.x += (tx - k.position.x) * Math.min(1, dt * 6);
    k.position.z += (tz - k.position.z) * Math.min(1, dt * 6);
    const s = sel ? 1.15 : 0.95;
    k.scale.setScalar(k.scale.x + (s - k.scale.x) * Math.min(1, dt * 6));
    if (sel) {
      k.rotation.y = Math.sin(t * 1.2) * 0.5;
      animKid(k, dt, 0, false, 'cheer');
    } else {
      k.rotation.y += (0 - k.rotation.y) * Math.min(1, dt * 4);
      animKid(k, dt, 0.0, false);
      k.userData.body.position.y = Math.abs(Math.sin(t * 2 + i)) * 0.03;
    }
  });
  scene.children.forEach(o => { if (o.userData.float !== undefined) o.position.y += Math.sin(t + o.userData.float) * dt * 0.3; });
  const target = menuKids[selIndex] ? menuKids[selIndex].position.x * 0.5 : 0;
  camera.position.x += (target - camera.position.x) * Math.min(1, dt * 3);
  camera.position.y = 3.0; camera.position.z = 8.5;
  const ly = curScreen === 'scr-select' && window.innerWidth > window.innerHeight ? 0.1 : 1.3;
  menuLookY += (ly - menuLookY) * Math.min(1, dt * 4);
  camera.lookAt(camera.position.x * 0.8, menuLookY, 0);
}

// ================= ЭКРАНЫ =================
const screens = ['scr-menu', 'scr-select', 'scr-map', 'scr-shop', 'scr-intro', 'scr-pause', 'scr-result', 'scr-help', 'scr-settings'];
let curScreen = 'scr-menu';
function show(id) {
  screens.forEach(s => { const el = document.getElementById(s); if (el) el.classList.toggle('hidden', s !== id); });
  curScreen = id;
  const inGame = mode === 'game';
  $('#hud').classList.toggle('hidden', !inGame || (id && id !== null));
  $('#controls').classList.toggle('hidden', !inGame || (id && id !== null));
  document.querySelectorAll('.coins-pill').forEach(e => e.textContent = '🪙 ' + save.coins);
}

function goMenu() {
  if (mode === 'game') endGameScene();
  if (!menuKids.length || mode !== 'menu') buildMenuScene();
  mode = 'menu';
  playMusic('menu');
  show('scr-menu');
}
function goSelect() { if (mode !== 'menu') { endGameScene(); mode = 'menu'; buildMenuScene(); } renderCharCard(); show('scr-select'); }

function renderCharCard() {
  const c = CHARS[selIndex], s = save.chars[c.id], st = charStats(c.id);
  const bar = (v, max) => `<div class="bar"><i style="width:${Math.min(100, v / max * 100)}%"></i></div>`;
  $('#charCard').innerHTML = `
    <div class="cc-head"><span class="cc-emoji">${c.emoji}</span>
      <div><div class="cc-name">${charName(c)}</div><div class="cc-title">${c.title} · Ур. ${s.level}</div></div></div>
    <div class="xp">${bar(s.xp, xpNeed(s.level))}<small>Опыт ${s.xp}/${xpNeed(s.level)}</small></div>
    <div class="cc-perk">${c.perk}</div>
    <div class="stats">
      <span>⚡ Скорость</span>${bar(st.speed, 10)}
      <span>🦘 Прыжок</span>${bar(st.jump, 13)}
      <span>💨 Рывок</span>${bar(st.stamina, 15)}
      <span>👊 Сила</span>${bar(st.power, 4)}
      <span>❤️ Жизни</span><b>${'❤️'.repeat(st.hp)}</b>
    </div>
    ${c.custom ? '<button class="btn small" id="btnRename">✏️ Изменить имя</button>' : ''}`;
  const rn = $('#btnRename');
  if (rn) rn.onclick = () => {
    const n = prompt('Как зовут твоего героя?', save.heroName || 'Новичок');
    if (n && n.trim()) {
      save.heroName = n.trim().slice(0, 12); writeSave();
      buildMenuScene(); renderCharCard();
    }
  };
}

function renderShop() {
  const c = CHARS[selIndex], s = save.chars[c.id];
  $('#shopTitle').textContent = `Прокачка: ${charName(c)} ${c.emoji}`;
  $('#shopList').innerHTML = UPGRADES.map(u => {
    const lv = s.up[u.id], maxed = lv >= u.max, cost = upgradeCost(u, lv);
    return `<div class="up">
      <div class="up-ico">${u.emoji}</div>
      <div class="up-info"><b>${u.name}</b> <small>${u.desc}</small>
        <div class="pips">${Array.from({ length: u.max }, (_, i) => `<i class="${i < lv ? 'on' : ''}"></i>`).join('')}</div></div>
      <button class="btn buy ${maxed || save.coins < cost ? 'off' : ''}" data-up="${u.id}">${maxed ? 'МАКС' : '🪙 ' + cost}</button>
    </div>`;
  }).join('');
  document.querySelectorAll('#shopList .buy').forEach(b => b.onclick = () => {
    const u = UPGRADES.find(x => x.id === b.dataset.up), lv = s.up[u.id];
    if (lv >= u.max) return;
    const cost = upgradeCost(u, lv);
    if (save.coins < cost) { SFX.bad(); toast('Не хватает монет! Пройди уровни 🪙'); return; }
    save.coins -= cost; s.up[u.id]++; writeSave(); SFX.levelup();
    renderShop(); show('scr-shop');
  });
}

function isUnlocked(w, d) {
  if (w === 0 && d === 0) return true;
  if (d > 0) return !!save.done[w + '_' + (d - 1)];
  return !!save.done[(w - 1) + '_0'];
}
function renderMap() {
  let total = 0;
  $('#worldList').innerHTML = WORLDS.map((W, wi) => {
    const lv = [0, 1, 2].map(d => {
      const st = save.done[wi + '_' + d] || 0; total += st;
      const un = isUnlocked(wi, d);
      return `<button class="lvl ${un ? '' : 'locked'}" data-w="${wi}" data-d="${d}">
        ${un ? `<b>${d + 1}</b><span>${'★'.repeat(st)}${'☆'.repeat(3 - st)}</span>` : '🔒'}</button>`;
    }).join('');
    return `<div class="world" style="--wc:${W.color}"><div class="w-emoji">${W.emoji}</div>
      <div class="w-body"><div class="w-name">${W.name}</div><div class="w-desc">${W.short}</div><div class="lvls">${lv}</div></div></div>`;
  }).join('');
  $('#totalStars').textContent = `★ ${total} / ${WORLDS.length * 9}`;
  document.querySelectorAll('.lvl').forEach(b => b.onclick = () => {
    const w = +b.dataset.w, d = +b.dataset.d;
    if (!isUnlocked(w, d)) { SFX.bad(); toast(d > 0 ? 'Сначала пройди предыдущий уровень этого мира' : 'Пройди 1-й уровень предыдущего мира'); return; }
    SFX.click(); openIntro(w, d);
  });
}

function openIntro(w, d) {
  pendingLevel = { w, d };
  const W = WORLDS[w];
  $('#introTitle').innerHTML = `${W.emoji} ${W.name} <small>· уровень ${d + 1}</small>`;
  $('#introText').innerHTML = `<p>${W.desc}</p><ul>${W.how.map(h => `<li>${h}</li>`).join('')}</ul>
    <p class="diff">Сложность: ${['🟢 Лёгкий', '🟡 Средний', '🔴 Трудный'][d]}</p>`;
  show('scr-intro');
}

// ================= ИГРА =================
function newLevel(o) {
  const lvl = Object.assign({
    colliders: [], floor: true, coins: [], spawn: { x: 0, y: 0, z: 0 }, timeLimit: 90,
    camOffset: new THREE.Vector3(0, 9, 10.5), actionLabel: null, onTimeUp: 'lose', killY: -12,
    speedMul: 1, update() { }, onAction() { }, goal() { return ''; }, ents: [], lavaY: null
  }, o);
  lvl.scene = baseScene(o.sky, o.fog);
  return lvl;
}

function addGround(Lv, size, tex, color) {
  const m = new THREE.MeshLambertMaterial({ color: color || 0xffffff, map: tex || null });
  const g = mesh(new THREE.PlaneGeometry(size, size), m, 0, 0, 0, false);
  g.rotation.x = -Math.PI / 2; g.receiveShadow = true;
  Lv.scene.add(g);
  return g;
}
function addFence(Lv, half, h, color) {
  const t = 0.4, c = color || 0xb5835a;
  addBlock(Lv, 0, -half - t / 2, half * 2 + t * 2, t, h, c);
  addBlock(Lv, 0, half + t / 2, half * 2 + t * 2, t, h, c);
  addBlock(Lv, -half - t / 2, 0, t, half * 2, h, c);
  addBlock(Lv, half + t / 2, 0, t, half * 2, h, c);
}
function addCoin(Lv, x, y, z) {
  const c = makeCoin(); c.position.set(x, (y || 0) + 0.8, z);
  Lv.scene.add(c);
  Lv.coins.push({ m: c, taken: false, baseY: (y || 0) + 0.8 });
}
function scatterCoins(Lv, n, half) {
  for (let i = 0; i < n; i++) { const p = randomFreeSpot(Lv, half, 0.6); addCoin(Lv, p.x, 0, p.z); }
}

// Частицы
const particles = [];
function burst(pos, color, n, spd) {
  for (let i = 0; i < (n || 14); i++) {
    const m = mesh(G_BOX, mat(Array.isArray(color) ? pick(color) : color), pos.x, pos.y + 0.8, pos.z, false);
    m.scale.setScalar(rand(0.08, 0.18));
    const s = spd || 5;
    m.userData.v = new THREE.Vector3(rand(-s, s), rand(2, s * 1.4), rand(-s, s));
    m.userData.life = rand(0.6, 1.1);
    scene.add(m); particles.push(m);
  }
}
function updateParticles(dt) {
  for (let i = particles.length - 1; i >= 0; i--) {
    const p = particles[i];
    p.userData.life -= dt;
    p.userData.v.y -= 15 * dt;
    p.position.addScaledVector(p.userData.v, dt);
    p.rotation.x += dt * 8; p.rotation.y += dt * 6;
    if (p.userData.life <= 0) { p.parent && p.parent.remove(p); particles.splice(i, 1); }
  }
}

let toastTimer = 0;
function toast(t, ms) {
  const el = $('#toast'); el.textContent = t; el.classList.add('on');
  clearTimeout(toastTimer); toastTimer = setTimeout(() => el.classList.remove('on'), ms || 1800);
}
function bigMsg(t, color, ms) {
  const el = $('#bigMsg');
  el.textContent = t; el.style.color = color || '#fff'; el.classList.add('on');
  clearTimeout(el._t);
  if (ms !== 0) el._t = setTimeout(() => el.classList.remove('on'), ms || 1200);
}
function hideBigMsg() { $('#bigMsg').classList.remove('on'); }

function startLevel(w, d) {
  endGameScene();
  const W = WORLDS[w];
  const cid = CHARS[selIndex].id;
  save.chosen = cid; writeSave();
  const st = charStats(cid);
  G = { w, d, time: 0, coins: 0, hpLost: 0, over: false, paused: false, cid, st, progress: null };
  L = W.build(d, st);
  disposeScene(scene);
  scene = L.scene;
  // игрок
  const kid = makeKid(kidOptsFor(cid, L.costume));
  scene.add(kid);
  P = {
    mesh: kid, pos: new THREE.Vector3(L.spawn.x, L.spawn.y || 0, L.spawn.z), vel: new THREE.Vector3(),
    r: 0.38, h: kid.userData.topY - 0.3, onGround: false, ground: null, hp: st.hp, maxHp: st.hp,
    inv: 0, stamina: st.stamina, st, coyote: 0, locked: false, yaw: L.spawnYaw || Math.PI, stun: 0
  };
  kid.rotation.y = P.yaw;
  L.checkpoint = { x: L.spawn.x, y: L.spawn.y || 0, z: L.spawn.z };
  L.timeLimit = Math.round(L.timeLimit * st.time);
  if (L.init) L.init(P);
  // стрелка-подсказка
  const arrow = new THREE.Mesh(new THREE.ConeGeometry(0.28, 0.7, 4), new THREE.MeshBasicMaterial({ color: 0xffe14d, transparent: true, opacity: 0.9 }));
  arrow.rotation.x = Math.PI / 2;
  const arrowG = new THREE.Group(); arrowG.add(arrow); arrowG.visible = false; scene.add(arrowG);
  G.arrow = arrowG;
  mode = 'game';
  // кнопки
  const ab = $('#btnAction');
  ab.classList.toggle('hidden', !L.actionLabel);
  ab.textContent = L.actionLabel || '';
  $('#btnJump').classList.toggle('hidden', !!L.noJump);
  $('#hudProg').classList.add('hidden');
  updateHud();
  playMusic(L.music || 'play');
  show(null);
  camera.position.copy(P.pos).add(L.camOffset);
  camera.lookAt(P.pos.x, P.pos.y + 1, P.pos.z);
  bigMsg('СТАРТ!', '#ffe14d', 1000);
  SFX.good();
}

function endGameScene() {
  particles.length = 0;
  hideBigMsg();
  if (mode === 'game') {
    mode = 'menu';
    disposeScene(scene); scene = null;
    menuKids = [];
    L = null; P = null;
  }
}

function hurt(respawn, msg) {
  if (!P || P.inv > 0 || G.over) return;
  P.hp--; G.hpLost++;
  P.inv = 1.6;
  SFX.hit();
  burst(P.pos, [0xff3b3b, 0xffffff], 12);
  if (navigator.vibrate) try { navigator.vibrate(120); } catch (e) { }
  if (msg) toast(msg);
  if (P.hp <= 0) { lose('Закончились жизни 💔'); return; }
  if (respawn) respawnPlayer();
}
function respawnPlayer() {
  const c = L.checkpoint;
  P.pos.set(c.x, c.y + 0.3, c.z); P.vel.set(0, 0, 0); P.locked = false;
  if (L.onRespawn) L.onRespawn();
}

function playerUpdate(dt) {
  readKeys();
  const st = P.st;
  if (P.inv > 0) { P.inv -= dt; P.mesh.visible = Math.floor(P.inv * 12) % 2 === 0 || P.inv <= 0; }
  else P.mesh.visible = true;
  if (P.stun > 0) P.stun -= dt;
  let mx = input.x, mz = input.z;
  const len = Math.hypot(mx, mz); if (len > 1) { mx /= len; mz /= len; }
  const moving = len > 0.15;
  let spd = st.speed * L.speedMul;
  const sprint = input.sprint && moving && P.stamina > 0.05;
  if (sprint) { spd *= 1.5; P.stamina = Math.max(0, P.stamina - dt); }
  else P.stamina = Math.min(st.stamina, P.stamina + dt * 0.6);
  if (P.stun > 0) spd = 0;

  if (!P.locked) {
    const k = P.onGround ? 14 : 5;
    const f = 1 - Math.exp(-k * dt);
    P.vel.x += (mx * spd - P.vel.x) * f;
    P.vel.z += (mz * spd - P.vel.z) * f;
    if (P.onGround) P.coyote = 0.12; else P.coyote -= dt;
    if (input.jump && P.coyote > 0 && !L.noJump && P.stun <= 0) {
      P.vel.y = st.jump; P.coyote = 0; P.onGround = false; P.ground = null; SFX.jump();
    }
    const wasAir = !P.onGround;
    moveEntity(P, dt, L);
    if (wasAir && P.onGround && L.onLand) L.onLand(P.ground);
  }
  input.jump = false;

  // поворот
  const hs = Math.hypot(P.vel.x, P.vel.z);
  if (hs > 0.4) {
    const ty = Math.atan2(P.vel.x, P.vel.z);
    let d = ty - P.yaw; while (d > Math.PI) d -= Math.PI * 2; while (d < -Math.PI) d += Math.PI * 2;
    P.yaw += d * Math.min(1, dt * 12);
  }
  P.mesh.position.copy(P.pos);
  P.mesh.rotation.y = P.yaw;
  animKid(P.mesh, dt, Math.min(1, hs / 6), !P.onGround && !P.locked, P.carry ? 'carry' : null);

  // падение / лава
  if (P.pos.y < L.killY) { hurt(false, 'Упал! 😵'); if (!G.over) respawnPlayer(); }
  if (L.lavaY !== null && P.pos.y < L.lavaY + 0.12 && !G.over) {
    P.inv = 0; hurt(false, 'Горячо! Пол — это лава! 🔥');
    burst(P.pos, [0xff6a00, 0xffd000], 16);
    if (!G.over) respawnPlayer();
  }
}

function coinsUpdate(dt) {
  const t = performance.now() / 1000;
  for (const c of L.coins) {
    if (c.taken) continue;
    c.m.rotation.y += dt * 3;
    const dx = P.pos.x - c.m.position.x, dy = (P.pos.y + 0.8) - c.m.position.y, dz = P.pos.z - c.m.position.z;
    const d = Math.hypot(dx, dy, dz);
    if (d < P.st.magnet + 0.6) {
      c.m.position.x += dx * Math.min(1, dt * 10); c.m.position.y += dy * Math.min(1, dt * 10); c.m.position.z += dz * Math.min(1, dt * 10);
      if (d < 0.7) { c.taken = true; c.m.visible = false; G.coins++; SFX.coin(); }
    } else c.m.position.y = c.baseY + Math.sin(t * 3 + c.m.position.x) * 0.12;
  }
}

function cameraUpdate(dt) {
  const off = L.camOffset;
  const tx = P.pos.x + off.x, ty = P.pos.y + off.y, tz = P.pos.z + off.z;
  const f = 1 - Math.exp(-5 * dt);
  camera.position.x += (tx - camera.position.x) * f;
  camera.position.y += (ty - camera.position.y) * f;
  camera.position.z += (tz - camera.position.z) * f;
  camera.lookAt(P.pos.x, P.pos.y + 1.1, P.pos.z - (L.lookAhead || 0));
  const sun = scene.userData.sun;
  sun.position.set(P.pos.x + 10, P.pos.y + 22, P.pos.z + 8);
  sun.target.position.set(P.pos.x, P.pos.y, P.pos.z);
}

function fmtTime(s) { s = Math.max(0, Math.ceil(s)); return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0'); }
function updateHud() {
  if (!G || !L) return;
  const left = L.timeLimit - G.time;
  const tEl = $('#hudTime');
  tEl.textContent = (L.onTimeUp === 'win' ? '⏳ ' : '⏱ ') + fmtTime(left);
  tEl.classList.toggle('warn', left < 10);
  $('#hudGoal').innerHTML = L.goal();
  $('#hudHp').textContent = '❤️'.repeat(Math.max(0, P.hp)) + '🖤'.repeat(Math.max(0, P.maxHp - P.hp));
  $('#hudCoins').textContent = '🪙 ' + G.coins;
  $('#stamFill').style.width = (P.stamina / P.st.stamina * 100) + '%';
  if (G.progress !== null && G.progress !== undefined) {
    $('#hudProg').classList.remove('hidden');
    $('#hudProgFill').style.width = (G.progress * 100) + '%';
  } else $('#hudProg').classList.add('hidden');
}

function gameUpdate(dt) {
  if (G.over || G.paused) return;
  G.time += dt;
  resetColliderDeltas(L);
  L.update(dt, P);
  if (G.over) return;
  playerUpdate(dt);
  if (input.action) { input.action = false; if (L.actionLabel && !G.over) L.onAction(P); }
  coinsUpdate(dt);
  const tg = L.pointer ? L.pointer() : null;
  if (tg && !G.over) {
    const dx = tg.x - P.pos.x, dz = tg.z - P.pos.z, d = Math.hypot(dx, dz);
    G.arrow.visible = d > 3;
    G.arrow.position.set(P.pos.x + dx / d * 1.5, P.pos.y + 0.25 + Math.sin(G.time * 6) * 0.06, P.pos.z + dz / d * 1.5);
    G.arrow.rotation.y = Math.atan2(dx, dz);
  } else G.arrow.visible = false;
  if (G.time >= L.timeLimit && !G.over) {
    if (L.onTimeUp === 'win') win(); else lose('Время вышло ⏰');
  }
  cameraUpdate(dt);
  updateHud();
}

// отложенный вызов, который не сработает, если уровень уже сменился
function later(fn, ms) { const g = G; setTimeout(() => { if (G === g && !g.over) fn(); }, ms); }

function win() {
  if (G.over) return;
  G.over = true;
  const left = L.timeLimit - G.time;
  let stars = 1;
  if (L.onTimeUp === 'win') { stars += G.hpLost === 0 ? 2 : G.hpLost === 1 ? 1 : 0; }
  else { if (left / L.timeLimit >= 0.3) stars++; if (G.hpLost === 0) stars++; }
  finish(true, stars);
}
function lose(reason) {
  if (G.over) return;
  G.over = true;
  G.reason = reason;
  finish(false, 0);
}

function finish(won, stars) {
  input.x = input.z = 0; input.action = input.actionHeld = false;
  const c = charById(G.cid), s = save.chars[G.cid];
  const coinsGot = Math.round((G.coins * 3 + (won ? 25 + G.d * 20 + stars * 10 : 5)) * P.st.luck);
  const xpGot = won ? 35 + G.d * 25 + stars * 10 : 12;
  save.coins += coinsGot;
  s.xp += xpGot;
  let leveled = false;
  while (s.xp >= xpNeed(s.level) && s.level < 30) { s.xp -= xpNeed(s.level); s.level++; leveled = true; }
  const key = G.w + '_' + G.d;
  const wasNew = won && !save.done[key];
  if (won) save.done[key] = Math.max(save.done[key] || 0, stars);
  writeSave();
  if (won) { SFX.win(); burst(P.pos, KID_COLORS, 40, 7); bigMsg('ПОБЕДА!', '#7CFF6B', 1500); }
  else { SFX.lose(); bigMsg(G.reason || 'Проигрыш', '#ff6b6b', 1500); }
  setTimeout(() => {
    const W = WORLDS[G.w];
    $('#resTitle').textContent = won ? '🏆 Победа!' : '😢 Не получилось';
    $('#resStars').innerHTML = won ? '★'.repeat(stars) + '<span class="dim">' + '★'.repeat(3 - stars) + '</span>' : '<span class="dim">★★★</span>';
    $('#resText').innerHTML = `
      ${won ? '' : `<p>${G.reason || ''}</p>`}
      <p>${W.emoji} ${W.name} · уровень ${G.d + 1}</p>
      <p>🪙 +${coinsGot} монет &nbsp; ✨ +${xpGot} опыта</p>
      ${leveled ? `<p class="lvup">🎉 ${charName(c)} получил уровень ${s.level}!${s.level === 3 ? ' Новая кепка!' : s.level === 8 ? ' Корона!' : ''}</p>` : ''}
      ${wasNew && isUnlocked(G.w, G.d + 1) && G.d < 2 ? '<p>🔓 Открыт следующий уровень!</p>' : ''}
      ${wasNew && G.d === 0 && G.w + 1 < WORLDS.length ? `<p>🔓 Открыт мир: ${WORLDS[G.w + 1].emoji} ${WORLDS[G.w + 1].name}</p>` : ''}`;
    if (leveled) SFX.levelup();
    const next = nextLevel(G.w, G.d);
    $('#btnNext').classList.toggle('hidden', !won || !next);
    show('scr-result');
  }, 1600);
}
function nextLevel(w, d) {
  if (d < 2 && isUnlocked(w, d + 1)) return { w, d: d + 1 };
  if (w + 1 < WORLDS.length && isUnlocked(w + 1, 0)) return { w: w + 1, d: 0 };
  return null;
}

function togglePause() {
  if (mode !== 'game' || !G || G.over) return;
  G.paused = !G.paused;
  if (G.paused) show('scr-pause'); else { show(null); clock.getDelta(); }
}

// ================= ЦИКЛ =================
function loop() {
  requestAnimationFrame(loop);
  const dt = Math.min(clock.getDelta(), 0.05);
  if (mode === 'menu' && scene) updateMenu(dt);
  else if (mode === 'game' && G) gameUpdate(dt);
  updateParticles(dt);
  if (scene) renderer.render(scene, camera);
}

// ================= КНОПКИ =================
function wire() {
  const on = (id, fn) => { const el = document.getElementById(id); if (el) el.onclick = () => { audio(); SFX.click(); fn(); }; };
  on('btnPlay', () => goSelect());
  on('btnHelp', () => show('scr-help'));
  on('btnSettings', () => { renderSettings(); show('scr-settings'); });
  on('btnHelpBack', () => show('scr-menu'));
  on('btnSetBack', () => show('scr-menu'));
  on('btnSelBack', () => show('scr-menu'));
  on('btnPrev', () => { selIndex = (selIndex + CHARS.length - 1) % CHARS.length; renderCharCard(); });
  on('btnNextChar', () => { selIndex = (selIndex + 1) % CHARS.length; renderCharCard(); });
  on('btnShop', () => { renderShop(); show('scr-shop'); });
  on('btnShopBack', () => { renderCharCard(); show('scr-select'); });
  on('btnToMap', () => { save.chosen = CHARS[selIndex].id; writeSave(); renderMap(); show('scr-map'); });
  on('btnMapBack', () => { renderCharCard(); show('scr-select'); });
  on('btnIntroBack', () => { renderMap(); show('scr-map'); });
  on('btnStart', () => startLevel(pendingLevel.w, pendingLevel.d));
  on('btnPause', () => togglePause());
  on('btnResume', () => togglePause());
  on('btnRestart', () => startLevel(G.w, G.d));
  on('btnQuit', () => { goMenu(); renderMap(); show('scr-map'); });
  on('btnRetry', () => startLevel(G.w, G.d));
  on('btnNext', () => { const n = nextLevel(G.w, G.d); if (n) { goMenu(); openIntro(n.w, n.d); } });
  on('btnResMap', () => { goMenu(); renderMap(); show('scr-map'); });
  on('btnResUp', () => { goMenu(); renderShop(); show('scr-shop'); });
  // свайп героев на экране выбора
  let sx = null;
  const sel = $('#scr-select');
  sel.addEventListener('touchstart', e => { sx = e.touches[0].clientX; }, { passive: true });
  sel.addEventListener('touchend', e => {
    if (sx === null) return;
    const dx = e.changedTouches[0].clientX - sx; sx = null;
    if (Math.abs(dx) > 60 && e.target.closest('#charCard') === null) {
      selIndex = (selIndex + (dx < 0 ? 1 : CHARS.length - 1)) % CHARS.length; SFX.click(); renderCharCard();
    }
  }, { passive: true });
  // тап по 3D-герою
  canvas.addEventListener('click', e => {
    if (mode !== 'menu' || curScreen !== 'scr-select') return;
    const x = e.clientX / window.innerWidth * 2 - 1, y = -(e.clientY / window.innerHeight) * 2 + 1;
    const rc = new THREE.Raycaster(); rc.setFromCamera(new THREE.Vector2(x, y), camera);
    const hit = rc.intersectObjects(menuKids, true)[0];
    if (hit) {
      let o = hit.object; while (o.parent && !menuKids.includes(o)) o = o.parent;
      const i = menuKids.indexOf(o); if (i >= 0) { selIndex = i; SFX.click(); renderCharCard(); }
    }
  });
  document.addEventListener('visibilitychange', () => { if (document.hidden && mode === 'game' && G && !G.paused && !G.over) togglePause(); });
}

function renderSettings() {
  $('#setList').innerHTML = `
    <label class="tog"><input type="checkbox" id="optSound" ${save.sound ? 'checked' : ''}> 🔊 Звуки</label>
    <label class="tog"><input type="checkbox" id="optMusic" ${save.music ? 'checked' : ''}> 🎵 Музыка</label>
    <label class="tog"><input type="checkbox" id="optShadows" ${save.shadows !== false ? 'checked' : ''}> 🌗 Тени (выключи, если игра тормозит)</label>
    <button class="btn danger" id="btnReset">🗑 Сбросить прогресс</button>`;
  $('#optShadows').onchange = e => { save.shadows = e.target.checked; writeSave(); renderer.shadowMap.enabled = save.shadows; clearMatCache(); };
  $('#optSound').onchange = e => { save.sound = e.target.checked; writeSave(); };
  $('#optMusic').onchange = e => { save.music = e.target.checked; writeSave(); if (save.music) { musicTheme = null; playMusic('menu'); } else stopMusic(); };
  $('#btnReset').onclick = () => {
    if (confirm('Точно стереть весь прогресс, монеты и прокачку?')) { localStorage.removeItem(SAVE_KEY); loadSave(); buildMenuScene(); toast('Прогресс сброшен'); show('scr-menu'); }
  };
}

// Кнопка «Назад» на Android
window.onAndroidBack = function () {
  if (mode === 'game' && G && !G.over) { togglePause(); return 'ok'; }
  const back = {
    'scr-select': 'scr-menu', 'scr-help': 'scr-menu', 'scr-settings': 'scr-menu',
    'scr-map': 'scr-select', 'scr-shop': 'scr-select', 'scr-intro': 'scr-map'
  };
  if (curScreen === 'scr-menu') return 'exit';
  if (curScreen === 'scr-result') { goMenu(); renderMap(); show('scr-map'); return 'ok'; }
  const to = back[curScreen];
  if (to) { if (to === 'scr-map') renderMap(); if (to === 'scr-select') renderCharCard(); show(to); return 'ok'; }
  return 'exit';
};

// ================= СТАРТ =================
resize();
setupInput();
wire();
buildMenuScene();
show('scr-menu');
document.body.addEventListener('pointerdown', () => { audio(); if (!musicTimer && mode === 'menu') playMusic('menu'); }, { once: true });
loop();
setTimeout(() => { const s = $('#splash'); if (s) s.classList.add('gone'); }, 400);
