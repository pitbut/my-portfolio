'use strict';
/* ===== Миры и уровни ===== */
const V3 = (x, y, z) => new THREE.Vector3(x, y, z);

// ---- помощники для NPC ----
function ent(m, x, z, y) {
  return { mesh: m, pos: V3(x, y || 0, z), vel: V3(0, 0, 0), r: 0.36, h: 1.4, onGround: true, ground: null, yaw: 0 };
}
function steer(e, dx, dz, speed, dt, Lv, k) {
  const d = Math.hypot(dx, dz);
  const f = 1 - Math.exp(-(k || 8) * dt);
  const tx = d > 0.001 ? dx / d * speed : 0, tz = d > 0.001 ? dz / d * speed : 0;
  e.vel.x += (tx - e.vel.x) * f; e.vel.z += (tz - e.vel.z) * f;
  e.bumped = false;
  moveEntity(e, dt, Lv);
  syncEnt(e, dt);
}
function syncEnt(e, dt) {
  e.mesh.position.copy(e.pos);
  const hs = Math.hypot(e.vel.x, e.vel.z);
  if (hs > 0.3) {
    const ty = Math.atan2(e.vel.x, e.vel.z);
    let d = ty - e.yaw; while (d > Math.PI) d -= Math.PI * 2; while (d < -Math.PI) d += Math.PI * 2;
    e.yaw += d * Math.min(1, dt * 10);
  }
  e.mesh.rotation.y = e.yaw;
  return hs;
}
const dist2D = (a, b) => Math.hypot(a.x - b.x, a.z - b.z);
const windowTex = (wall, win) => canvasTex(64, (c, s) => {
  c.fillStyle = wall; c.fillRect(0, 0, s, s);
  for (let y = 6; y < s; y += 20) for (let x = 6; x < s; x += 20) {
    c.fillStyle = Math.random() < 0.35 ? '#ffe58a' : win; c.fillRect(x, y, 11, 13);
  }
}, 1);

const BRICK_COLORS = [
  { c: 0xe53935, e: '🟥', n: 'красный' }, { c: 0x1e88e5, e: '🟦', n: 'синий' }, { c: 0xfdd835, e: '🟨', n: 'жёлтый' },
  { c: 0x43a047, e: '🟩', n: 'зелёный' }, { c: 0xfb8c00, e: '🟧', n: 'оранжевый' }, { c: 0x8e24aa, e: '🟪', n: 'фиолетовый' }
];
const G_STUD = new THREE.CylinderGeometry(0.13, 0.13, 0.12, 10);
function makeBrick(color) {
  const g = new THREE.Group();
  const b = mesh(G_BOX, mat(color), 0, 0, 0); b.scale.set(1.6, 0.6, 0.8); g.add(b);
  for (let i = 0; i < 4; i++) for (let j = 0; j < 2; j++) g.add(mesh(G_STUD, mat(color), -0.6 + i * 0.4, 0.35, -0.2 + j * 0.4));
  return g;
}

const WORLDS = [
  // ================= 1. ЛЕГО =================
  {
    id: 'lego', name: 'Лего-стройка', emoji: '🧱', color: '#ff595e',
    short: 'Собери конструктор на время',
    desc: 'Огромный конструктор рассыпался по площадке! Собери постройку деталь за деталью, пока не кончилось время.',
    how: ['Подойди к детали — герой поднимет её над головой', 'Неси на серую площадку в центре', 'Нужен деталь того цвета, что указан сверху (жёлтая стрелка подскажет)', '⬇️ — бросить деталь, если взял не ту', 'На сложных уровнях робот-пылесос выбивает детали из рук!'],
    build(d, st) {
      const Lv = newLevel({ sky: 0xaee3ff, timeLimit: [100, 120, 140][d], actionLabel: '⬇️', camOffset: V3(0, 10, 11) });
      const sc = Lv.scene;
      const stud = canvasTex(64, (c, s) => {
        c.fillStyle = '#43a047'; c.fillRect(0, 0, s, s);
        c.fillStyle = 'rgba(0,0,0,0.18)'; c.beginPath(); c.arc(s / 2 + 3, s / 2 + 3, s * 0.27, 0, 7); c.fill();
        c.fillStyle = '#5cbf60'; c.beginPath(); c.arc(s / 2, s / 2, s * 0.27, 0, 7); c.fill();
      }, 44);
      addGround(Lv, 44, stud);
      addFence(Lv, 20, 1.2, 0xffca3a);
      const zone = mesh(G_BOX, mat(0xcfd8dc), 0, 0.08, 0, false); zone.scale.set(5, 0.16, 3.6); sc.add(zone);
      const beam = new THREE.Mesh(new THREE.CylinderGeometry(2.6, 2.6, 12, 24, 1, true), new THREE.MeshBasicMaterial({ color: 0xffff88, transparent: true, opacity: 0.18, side: THREE.DoubleSide, depthWrite: false }));
      beam.position.y = 6; beam.visible = false; sc.add(beam);
      // большие кубики-препятствия
      for (let i = 0; i < 7; i++) {
        const p = randomFreeSpot(Lv, 16, 2.5, [{ x: 0, z: 0, r: 6 }, { x: 0, z: 8, r: 3 }]);
        const col = pick(BRICK_COLORS).c, h = pick([1.2, 1.8, 2.4]);
        addBlock(Lv, p.x, p.z, 2, 2, h, col);
        for (let a = 0; a < 2; a++) for (let b = 0; b < 2; b++) { const sd = mesh(G_STUD, mat(col), p.x - 0.5 + a, h + 0.08, p.z - 0.5 + b); sd.scale.set(2.2, 1.5, 2.2); sc.add(sd); }
      }
      const N = [8, 12, 16][d], ncol = 3 + d;
      const palette = BRICK_COLORS.slice(0, ncol);
      const slots = [];
      for (let i = 0; i < N; i++) {
        const layer = Math.floor(i / 4), j = i % 4;
        const col = pick(palette);
        const pos = V3(j % 2 ? 0.8 : -0.8, 0.16 + 0.3 + layer * 0.72, j < 2 ? -0.4 : 0.4);
        const ghost = makeBrick(col.c);
        ghost.traverse(o => { if (o.isMesh) { o.material = new THREE.MeshBasicMaterial({ color: col.c, transparent: true, opacity: 0.35, depthWrite: false }); o.castShadow = false; } });
        ghost.position.copy(pos); ghost.visible = false; sc.add(ghost);
        slots.push({ col, pos, ghost });
      }
      const loose = [];
      const spawnBrick = (col) => {
        const p = randomFreeSpot(Lv, 18, 1.2, [{ x: 0, z: 0, r: 5 }]);
        const b = makeBrick(col.c); b.position.set(p.x, 0.3, p.z); b.rotation.y = rand(0, 3);
        sc.add(b);
        const mk = new THREE.Mesh(new THREE.ConeGeometry(0.25, 0.5, 4), new THREE.MeshBasicMaterial({ color: 0xffe14d }));
        mk.rotation.x = Math.PI; mk.visible = false; sc.add(mk);
        const o = { m: b, col, cool: 0, mk }; loose.push(o); return o;
      };
      slots.forEach(s => spawnBrick(s.col));
      for (let i = 0; i < 2 + d * 2; i++) spawnBrick(pick(palette));
      scatterCoins(Lv, 10, 17);
      // роботы-пылесосы
      const robots = [];
      for (let i = 0; i < [0, 1, 3][d]; i++) {
        const g = new THREE.Group();
        const bodyR = mesh(G_CYL, mat(0x37474f), 0, 0.18, 0); bodyR.scale.set(0.7, 0.3, 0.7); g.add(bodyR);
        const led = mesh(G_SPH, mat(0xff1744, { emissive: 0xaa0000 }), 0, 0.38, 0.4); led.scale.setScalar(0.1); g.add(led);
        const p = randomFreeSpot(Lv, 16, 1.5, [{ x: 0, z: 8, r: 6 }]);
        g.position.set(p.x, 0, p.z); sc.add(g);
        const a = rand(0, 6.28);
        robots.push({ m: g, vx: Math.cos(a) * (2.5 + d * 0.5), vz: Math.sin(a) * (2.5 + d * 0.5), hitCd: 0 });
      }
      let placed = 0, warnCd = 0, flying = [];
      Lv.spawn = { x: 0, z: 8 };
      Lv.need = () => slots[placed] && slots[placed].col;
      Lv.goal = () => {
        const n = Lv.need();
        return `🧱 ${placed}/${N} &nbsp; Нужен: ${n ? n.e : '✅'}${P.carry ? ' &nbsp;В руках: ' + P.carry.col.e : ''}`;
      };
      Lv.pointer = () => {
        if (P.carry) return { x: 0, z: 0 };
        const n = Lv.need(); if (!n) return null;
        let best = null, bd = 1e9;
        for (const b of loose) if (b.col === n && !b.held) { const dd = dist2D(b.m.position, P.pos); if (dd < bd) { bd = dd; best = b.m.position; } }
        return best;
      };
      const drop = (toRandom) => {
        const b = P.carry; if (!b) return;
        P.mesh.remove(b.m); sc.add(b.m);
        b.held = false; b.cool = 1;
        if (toRandom) { const p = randomFreeSpot(Lv, 18, 1.2, [{ x: 0, z: 0, r: 5 }]); b.m.position.set(p.x, 0.3, p.z); }
        else b.m.position.set(P.pos.x + Math.sin(P.yaw) * 1.2, 0.3, P.pos.z + Math.cos(P.yaw) * 1.2);
        b.m.rotation.set(0, rand(0, 3), 0);
        P.carry = null;
      };
      Lv.onAction = () => { if (P.carry) { drop(false); SFX.click(); } else toast('Подойди к детали, чтобы взять её'); };
      Lv.update = (dt) => {
        const t = G.time;
        warnCd -= dt;
        const n = Lv.need();
        slots.forEach((s, i) => { s.ghost.visible = i === placed; if (i === placed) s.ghost.position.y = s.pos.y + Math.sin(t * 4) * 0.05; });
        beam.visible = !!P.carry;
        for (const b of loose) {
          if (b.held || b.placed) { b.mk.visible = false; continue; }
          b.cool -= dt;
          b.mk.visible = n && b.col === n;
          b.mk.position.set(b.m.position.x, 1.4 + Math.sin(t * 5) * 0.15, b.m.position.z);
          if (!P.carry && b.cool <= 0 && dist2D(b.m.position, P.pos) < 1.1 * st.reach + 0.3 && P.pos.y < 1.5) {
            P.carry = b; b.held = true; sc.remove(b.m); P.mesh.add(b.m);
            b.m.position.set(0, P.mesh.userData.topY + 0.45, 0); b.m.rotation.set(0, Math.PI / 2, 0);
            SFX.click();
          }
        }
        if (P.carry && Math.abs(P.pos.x) < 3.3 && Math.abs(P.pos.z) < 2.6) {
          if (n && P.carry.col === n) {
            const b = P.carry; P.mesh.remove(b.m); sc.add(b.m); P.carry = null;
            b.m.position.copy(P.pos).add(V3(0, 2, 0)); b.placed = true;
            flying.push({ b, from: b.m.position.clone(), to: slots[placed].pos.clone(), t: 0 });
            slots[placed].ghost.visible = false;
            placed++; SFX.good(); burst(slots[placed - 1].pos, [n.c, 0xffffff], 10);
            if (placed >= N) { later(win, 400); }
          } else if (warnCd <= 0) { warnCd = 1.5; SFX.bad(); toast(`Нужен ${n.n} цвет ${n.e}! Брось эту деталь ⬇️`); }
        }
        for (let i = flying.length - 1; i >= 0; i--) {
          const f = flying[i]; f.t += dt * 3;
          const k = Math.min(1, f.t);
          f.b.m.position.lerpVectors(f.from, f.to, k); f.b.m.position.y += Math.sin(k * Math.PI) * 1.2;
          f.b.m.rotation.set(0, 0, 0);
          if (k >= 1) flying.splice(i, 1);
        }
        for (const r of robots) {
          r.hitCd -= dt;
          r.m.position.x += r.vx * dt; r.m.position.z += r.vz * dt;
          if (Math.abs(r.m.position.x) > 19) { r.vx *= -1; r.m.position.x = clamp(r.m.position.x, -19, 19); }
          if (Math.abs(r.m.position.z) > 19) { r.vz *= -1; r.m.position.z = clamp(r.m.position.z, -19, 19); }
          if (!freeSpot(Lv, r.m.position.x, r.m.position.z, 0.7) || (Math.abs(r.m.position.x) < 3.2 && Math.abs(r.m.position.z) < 2.5)) {
            r.m.position.x -= r.vx * dt * 2; r.m.position.z -= r.vz * dt * 2;
            const a = rand(0, 6.28), sp = Math.hypot(r.vx, r.vz); r.vx = Math.cos(a) * sp; r.vz = Math.sin(a) * sp;
          }
          r.m.rotation.y += dt * 4;
          if (r.hitCd <= 0 && dist2D(r.m.position, P.pos) < 1.0 && P.pos.y < 0.8) {
            r.hitCd = 1.5;
            const dx = P.pos.x - r.m.position.x, dz = P.pos.z - r.m.position.z, dd = Math.hypot(dx, dz) || 1;
            P.vel.set(dx / dd * 9, 5, dz / dd * 9); P.stun = 0.4; SFX.hit();
            if (P.carry) { drop(true); toast('Робот-пылесос выбил деталь! 🤖'); }
          }
        }
      };
      Lv.onTimeUpCheck = true;
      return Lv;
    }
  },

  // ================= 2. ИГРА В КАЛЬМАРА =================
  {
    id: 'squid', name: 'Игра в кальмара', emoji: '🦑', color: '#ff2e88',
    short: 'Тише едешь — дальше будешь',
    desc: 'Тише едешь — дальше будешь! Доберись до финиша, но двигаться можно только когда кукла отвернулась.',
    how: ['🟢 Зелёный свет — беги вперёд!', '🔴 Красный свет — замри и не прыгай!', 'Если кукла увидит движение — потеряешь жизнь и откатишься назад', 'Добеги до красной линии раньше, чем кончится время', 'Рывок 💨 поможет быстрее пробежать отрезок'],
    build(d, st) {
      const Lv = newLevel({ sky: 0xbfe9ff, timeLimit: [60, 52, 46][d], camOffset: V3(0, 6.5, 9), lookAhead: 4, music: null });
      const sc = Lv.scene;
      const sand = noiseTex('#e8c98f', ['#d9b97a', '#f3dcaa', '#c9a36a'], 30);
      const g = addGround(Lv, 120, sand);
      const wallM = new THREE.MeshLambertMaterial({ map: canvasTex(128, (c, s) => { const gr = c.createLinearGradient(0, 0, 0, s); gr.addColorStop(0, '#9fe3ff'); gr.addColorStop(1, '#f9c6d8'); c.fillStyle = gr; c.fillRect(0, 0, s, s); c.fillStyle = '#ffffff'; for (let i = 0; i < 6; i++) { c.beginPath(); c.arc(Math.random() * s, Math.random() * s * 0.5, 10 + Math.random() * 10, 0, 7); c.fill(); } }, 4, 1) });
      addBlock(Lv, -15.5, -3, 1, 96, 7, wallM); addBlock(Lv, 15.5, -3, 1, 96, 7, wallM);
      addBlock(Lv, 0, 45, 32, 1, 7, wallM); addBlock(Lv, 0, -51, 32, 1, 7, wallM);
      const startL = mesh(G_BOX, mat(0xffffff), 0, 0.02, 30, false); startL.scale.set(30, 0.04, 0.4); sc.add(startL);
      const finL = mesh(G_BOX, mat(0xff1744), 0, 0.02, -34, false); finL.scale.set(30, 0.04, 0.6); sc.add(finL);
      sc.add(makeTree(0, -46, 2.2));
      // кукла
      const doll = makeKid({ height: 1.1, skin: 0xf6d6bd, shirt: 0xffd23f, pants: 0xff7f11, hair: 0x111111, hairStyle: 'pigtails' });
      const dress = mesh(new THREE.ConeGeometry(0.55, 0.9, 16), mat(0xff7f11), 0, 0.85, 0); doll.add(dress);
      doll.scale.setScalar(3.6); doll.position.set(0, 0, -42); sc.add(doll);
      const lamp = mesh(G_SPH, mat(0x00e676, { emissive: 0x00a040 }), 6, 7, -42); lamp.scale.setScalar(0.9); sc.add(lamp);
      const post = mesh(G_CYL, mat(0x555555), 6, 3.3, -42); post.scale.set(0.15, 6.6, 0.15); sc.add(post);
      // участники
      const npcs = [];
      for (let i = 0; i < 10; i++) {
        const m = randomKid({ shirt: 0x1d8f6e, pants: 0x1d8f6e, shoes: 0xffffff });
        const lab = textSprite(String(Math.floor(rand(10, 456))).padStart(3, '0'), '#fff', null, 1.2); lab.position.y = 2.2; m.add(lab);
        const e = ent(m, rand(-13, 13), rand(31, 36)); e.spd = rand(1.8, 3.6); e.react = rand(0.1, 0.55); e.out = false; e.yaw = Math.PI;
        sc.add(m); npcs.push(e);
      }
      for (let i = 0; i < 14; i++) addCoin(Lv, rand(-12, 12), 0, rand(-30, 26));
      Lv.spawn = { x: 0, z: 34 };
      Lv.spawnYaw = Math.PI;
      let phase = 'green', pt = 3, redT = 0, songT = 0;
      const gmul = [1, 0.8, 0.62][d];
      Lv.goal = () => `${phase === 'green' || phase === 'toGreen' ? '🟢 Беги!' : '🔴 Замри!'} &nbsp; до финиша ${Math.max(0, Math.round(P.pos.z + 34))} м`;
      Lv.pointer = () => ({ x: P.pos.x, z: -40 });
      bigMsg('🟢 ИДИ!', '#62ff7a', 900);
      Lv.update = (dt) => {
        pt -= dt;
        if (phase === 'green') {
          songT -= dt;
          if (songT <= 0) { songT = 0.28; beep(pick([523, 587, 659, 698, 784]), 0.2, 'triangle', 0.05); }
          doll.rotation.y += (Math.PI - doll.rotation.y) * Math.min(1, dt * 8);
          if (pt <= 0) { phase = 'toRed'; pt = 0.45; beep(220, 0.4, 'sawtooth', 0.07, 440); }
        } else if (phase === 'toRed') {
          doll.rotation.y += (0 - doll.rotation.y) * Math.min(1, dt * 10);
          if (pt <= 0) { phase = 'red'; pt = rand(1.8, 3.4); redT = 0; bigMsg('🔴 СТОЙ!', '#ff4b4b', pt * 1000); lamp.material = mat(0xff1744, { emissive: 0xa00000 }); }
        } else if (phase === 'red') {
          redT += dt;
          doll.rotation.y = Math.sin(G.time * 2) * 0.12;
          const hs = Math.hypot(P.vel.x, P.vel.z);
          if (redT > 0.3 && (hs > 0.7 || !P.onGround) && P.inv <= 0 && P.pos.z > -34) {
            bigMsg('ЗАМЕЧЕН! 👀', '#ff4b4b', 900);
            hurt(false, 'Кукла заметила движение!');
            if (!G.over) { P.pos.z = Math.min(34, P.pos.z + 8); P.vel.set(0, 0, 0); }
          }
          if (pt <= 0) { phase = 'toGreen'; pt = 0.4; }
        } else if (phase === 'toGreen') {
          doll.rotation.y += (Math.PI - doll.rotation.y) * Math.min(1, dt * 10);
          if (pt <= 0) { phase = 'green'; pt = rand(2.4, 5) * gmul; hideBigMsg(); bigMsg('🟢 ИДИ!', '#62ff7a', 700); lamp.material = mat(0x00e676, { emissive: 0x00a040 }); }
        }
        // NPC
        for (const e of npcs) {
          if (e.out) continue;
          const go = phase === 'green' || phase === 'toRed' || (phase === 'red' && redT < e.react - 0.3) || (phase === 'toGreen' && false);
          if (e.pos.z < -35) { e.vel.set(0, 0, 0); syncEnt(e, dt); animKid(e.mesh, dt, 0, false, 'cheer'); continue; }
          if (go) { steer(e, rand(-0.3, 0.3), -1, e.spd, dt, Lv); animKid(e.mesh, dt, e.spd / 5, false); }
          else {
            if (phase === 'red' && redT < e.react && e.react > 0.45 && redT > 0.32) {
              e.out = true; e.mesh.rotation.x = -1.45; e.mesh.position.y = 0.25; SFX.bad(); continue;
            }
            steer(e, 0, 0, 0, dt, Lv, 30); animKid(e.mesh, dt, 0, false);
          }
        }
        if (P.pos.z < -34.5) win();
      };
      return Lv;
    }
  },

  // ================= 3. ЗОМБИ-АПОКАЛИПСИС =================
  {
    id: 'zombie', name: 'Зомби-апокалипсис', emoji: '🧟', color: '#6abf4b',
    short: 'Собери топливо и улети на вертолёте',
    desc: 'Город захватили зомби! Собери канистры с топливом для вертолёта и улетай, пока тебя не окружили.',
    how: ['Собирай красные канистры ⛽ — стрелка покажет ближайшую', '👊 — удар: отбрасывает и оглушает зомби рядом', 'Зомби медленные, но их много — не давай себя окружить', 'Когда соберёшь все канистры, беги к вертолёту в центре'],
    build(d, st) {
      const Lv = newLevel({ sky: 0x3d3a5c, fog: [0x3d3a5c, 16, 52], timeLimit: [150, 165, 180][d], actionLabel: '👊', music: 'spooky', camOffset: V3(0, 10, 10) });
      const sc = Lv.scene;
      sc.userData.hemi.intensity = 0.6; sc.userData.sun.intensity = 0.7; sc.userData.sun.color.set(0xb0c0ff);
      addGround(Lv, 64, noiseTex('#555b61', ['#4a4f55', '#62686e', '#3e4247'], 16));
      for (const x of [-13.5, 0, 13.5]) { const r = mesh(G_BOX, mat(0xffe082), x, 0.01, 0, false); r.scale.set(0.25, 0.02, 60); sc.add(r); }
      addFence(Lv, 30, 2.5, 0x6d6d6d);
      const H = mesh(new THREE.CircleGeometry(3, 24), mat(0xffeb3b), 0, 0.02, 0, false); H.rotation.x = -Math.PI / 2; sc.add(H);
      for (const gx of [-21, -7, 7, 21]) for (const gz of [-21, -7, 7, 21]) {
        if (Math.random() < 0.25) continue;
        const w = rand(5, 7.5), dd = rand(5, 7.5), h = rand(3, 6.5);
        const m = new THREE.MeshLambertMaterial({ map: windowTex(pick(['#7b6f63', '#5f6b7a', '#8a7f72', '#6a5d5d']), '#2b2f3a') });
        m.map.repeat.set(Math.round(w / 2), Math.round(h / 2));
        addBlock(Lv, gx + rand(-1, 1), gz + rand(-1, 1), w, dd, h, m);
      }
      for (let i = 0; i < 7; i++) {
        const p = randomFreeSpot(Lv, 27, 2.5, [{ x: 0, z: 0, r: 5 }]);
        const car = makeCar(pick([0x8d3b3b, 0x3b5e8d, 0x8d8d3b, 0x666666])); car.position.set(p.x, 0, p.z);
        const rot = Math.random() < 0.5; if (rot) car.rotation.y = Math.PI / 2; sc.add(car);
        addCollider(Lv, p.x - (rot ? 1.9 : 0.9), p.x + (rot ? 1.9 : 0.9), p.z - (rot ? 0.9 : 1.9), p.z + (rot ? 0.9 : 1.9), 0, 1.5);
      }
      const K = [5, 7, 9][d];
      const cans = [];
      for (let i = 0; i < K; i++) {
        const p = randomFreeSpot(Lv, 27, 1, [{ x: 0, z: 4, r: 7 }, ...cans.map(c => ({ x: c.m.position.x, z: c.m.position.z, r: 6 }))]);
        const g = new THREE.Group();
        const b = mesh(G_BOX, mat(0xd32f2f, { emissive: 0x400000 }), 0, 0.4, 0); b.scale.set(0.55, 0.75, 0.3); g.add(b);
        const hd = mesh(G_BOX, mat(0x222222), 0, 0.85, 0); hd.scale.set(0.3, 0.12, 0.1); g.add(hd);
        const lab = textSprite('⛽', '#fff', null, 2); lab.position.y = 1.6; g.add(lab);
        g.position.set(p.x, 0, p.z); sc.add(g); cans.push({ m: g, got: false });
      }
      scatterCoins(Lv, 14, 27);
      const zombies = [];
      const spawnZ = () => {
        const p = randomFreeSpot(Lv, 27, 0.8, [{ x: P ? P.pos.x : 0, z: P ? P.pos.z : 4, r: 13 }]);
        const m = makeZombie(); sc.add(m);
        const e = ent(m, p.x, p.z); e.stun = 0; e.wt = 0; e.wx = 0; e.wz = 0; e.kb = V3(0, 0, 0);
        zombies.push(e);
      };
      const ZN = [6, 9, 13][d], zs = [2.2, 2.6, 3.0][d], sight = [12, 14, 17][d];
      let got = 0, heli = null, spawnT = 0, punchCd = 0;
      Lv.spawn = { x: 0, z: 4 };
      Lv.init = () => { for (let i = 0; i < ZN; i++) spawnZ(); };
      Lv.goal = () => got < K ? `⛽ Канистры ${got}/${K} &nbsp; 🧟 ${zombies.length}` : '🚁 Беги к вертолёту!';
      Lv.pointer = () => {
        if (got >= K) return { x: 0, z: 0 };
        let best = null, bd = 1e9;
        for (const c of cans) if (!c.got) { const dd = dist2D(c.m.position, P.pos); if (dd < bd) { bd = dd; best = c.m.position; } }
        return best;
      };
      const ring = new THREE.Mesh(new THREE.RingGeometry(0.5, 0.8, 24), new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.7, side: THREE.DoubleSide }));
      ring.rotation.x = -Math.PI / 2; ring.visible = false; sc.add(ring);
      let ringT = 0;
      Lv.onAction = () => {
        if (punchCd > 0) return;
        punchCd = 0.55; SFX.punch();
        ring.visible = true; ringT = 0; ring.position.set(P.pos.x, P.pos.y + 0.1, P.pos.z);
        const R = 2.3 * st.reach;
        let hit = 0;
        for (const z of zombies) {
          const dx = z.pos.x - P.pos.x, dz = z.pos.z - P.pos.z, dd = Math.hypot(dx, dz);
          if (dd < R) { z.kb.set(dx / (dd || 1) * 9 * st.power, 0, dz / (dd || 1) * 9 * st.power); z.stun = 1.6; hit++; burst(z.pos, [0x7fb069, 0xffffff], 6); }
        }
        if (hit) beep(90, 0.15, 'square', 0.1, 40);
      };
      Lv.update = (dt) => {
        punchCd -= dt;
        if (ring.visible) { ringT += dt; ring.scale.setScalar(1 + ringT * 8 * st.reach); ring.material.opacity = 0.7 - ringT * 2.5; if (ringT > 0.28) ring.visible = false; }
        const t = G.time;
        for (const c of cans) {
          if (c.got) continue;
          c.m.rotation.y += dt * 2; c.m.position.y = Math.sin(t * 3) * 0.1 + 0.1;
          if (dist2D(c.m.position, P.pos) < 1.0 * st.reach + 0.2) {
            c.got = true; sc.remove(c.m); got++; SFX.good(); burst(P.pos, [0xd32f2f, 0xffeb3b], 10);
            if (got >= K) {
              bigMsg('🚁 Вертолёт летит!', '#ffe14d', 1600);
              heli = new THREE.Group();
              const hb = mesh(G_SPH, mat(0x2e7d32), 0, 1.4, 0); hb.scale.set(1.5, 1.2, 2.2); heli.add(hb);
              const tail = mesh(G_BOX, mat(0x2e7d32), 0, 1.6, 3); tail.scale.set(0.3, 0.3, 3); heli.add(tail);
              const glass = mesh(G_SPH, mat(0x9fdcff), 0, 1.6, -1.2); glass.scale.set(1, 0.8, 1); heli.add(glass);
              const rot = mesh(G_BOX, mat(0x222222), 0, 2.8, 0); rot.scale.set(7, 0.08, 0.35); heli.add(rot); heli.userData.rot = rot;
              for (const sx of [-1, 1]) { const sk = mesh(G_BOX, mat(0x222222), sx, 0.1, 0); sk.scale.set(0.12, 0.12, 3); heli.add(sk); }
              heli.position.set(0, 20, 0); sc.add(heli);
            } else toast(`Канистра! Осталось ${K - got}`);
          }
        }
        if (heli) {
          heli.userData.rot.rotation.y += dt * 25;
          heli.position.y = Math.max(0, heli.position.y - dt * 6);
          if (heli.position.y <= 0.01 && dist2D(P.pos, heli.position) < 3.2) { burst(P.pos, KID_COLORS, 30); win(); }
        }
        if ([0, 25, 16][d] > 0) {
          spawnT += dt;
          if (spawnT > [0, 25, 16][d] && zombies.length < 22) { spawnT = 0; spawnZ(); toast('Ещё один зомби! 🧟'); }
        }
        for (const z of zombies) {
          if (z.stun > 0) {
            z.stun -= dt;
            z.pos.x += z.kb.x * dt; z.pos.z += z.kb.z * dt; z.kb.multiplyScalar(Math.exp(-4 * dt));
            z.vel.set(0, 0, 0); moveEntity(z, dt, Lv); syncEnt(z, dt);
            z.mesh.rotation.z = Math.sin(t * 20) * 0.2;
            continue;
          }
          z.mesh.rotation.z = 0;
          const dx = P.pos.x - z.pos.x, dz = P.pos.z - z.pos.z, dd = Math.hypot(dx, dz);
          if (dd < sight) steer(z, dx, dz, zs, dt, Lv, 4);
          else {
            z.wt -= dt;
            if (z.wt <= 0) { z.wt = rand(2, 4); const a = rand(0, 6.28); z.wx = Math.cos(a); z.wz = Math.sin(a); }
            steer(z, z.wx, z.wz, zs * 0.4, dt, Lv, 4);
          }
          animKid(z.mesh, dt, 0.6, false, 'zombie');
          if (dd < 0.85 && P.inv <= 0 && !heli?.landed) {
            hurt(false, 'Зомби тебя схватил! 🧟');
            P.vel.set(-dx / (dd || 1) * 10, 4, -dz / (dd || 1) * 10); P.stun = 0.3;
            z.stun = 1; z.kb.set(dx / (dd || 1) * 4, 0, dz / (dd || 1) * 4);
          }
        }
      };
      return Lv;
    }
  },

  // ================= 4. ПРЯТКИ =================
  {
    id: 'hide', name: 'Прятки', emoji: '🙈', color: '#ffca3a',
    short: 'Найди всех спрятавшихся',
    desc: 'Ты водишь! Друзья спрятались по двору — в кустах, за ящиками, в бочках и домиках. Найди всех!',
    how: ['Подойди к укрытию и нажми 🔍 «Искать»', 'Если укрытие пустое — потеряешь 3 секунды', 'Подсказка: укрытие, где кто-то сидит, иногда трясётся и оттуда слышен смешок 🤭', 'На трудном уровне друзья перебегают в другие укрытия!'],
    build(d, st) {
      const Lv = newLevel({ sky: 0x9fdcff, timeLimit: [90, 100, 115][d], actionLabel: '🔍' });
      const sc = Lv.scene;
      addGround(Lv, 52, noiseTex('#5fb35a', ['#4fa34a', '#6fc36a', '#58a852'], 20));
      addFence(Lv, 22, 1.3, 0xc58b5a);
      const base = mesh(G_BOX, mat(0x8d6e63), 0, 0.25, 15); base.scale.set(4, 0.5, 1); sc.add(base);
      const S = [10, 14, 18][d], K = [3, 5, 7][d];
      const spots = [];
      const types = ['bush', 'bush', 'box', 'tree', 'barrel', 'house', 'car'];
      for (let i = 0; i < S; i++) {
        const p = randomFreeSpot(Lv, 19, 2, [{ x: 0, z: 15, r: 5 }, ...spots.map(s => ({ x: s.x, z: s.z, r: 5 }))]);
        const ty = types[i % types.length];
        let obj;
        if (ty === 'bush') { obj = makeBush(p.x, p.z, 1.4); }
        else if (ty === 'tree') { obj = makeTree(p.x, p.z, 1.2); addCollider(Lv, p.x - 0.3, p.x + 0.3, p.z - 0.3, p.z + 0.3, 0, 3); }
        else if (ty === 'box') {
          obj = new THREE.Group(); obj.position.set(p.x, 0, p.z);
          const m = mesh(G_BOX, new THREE.MeshLambertMaterial({ map: canvasTex(64, (c, s) => { c.fillStyle = '#b8864b'; c.fillRect(0, 0, s, s); c.strokeStyle = '#7a5530'; c.lineWidth = 6; c.strokeRect(3, 3, s - 6, s - 6); c.beginPath(); c.moveTo(0, 0); c.lineTo(s, s); c.stroke(); }) }), 0, 0.8, 0); m.scale.set(1.6, 1.6, 1.6); obj.add(m);
          addCollider(Lv, p.x - 0.8, p.x + 0.8, p.z - 0.8, p.z + 0.8, 0, 1.6);
        } else if (ty === 'barrel') {
          obj = new THREE.Group(); obj.position.set(p.x, 0, p.z);
          const m = mesh(G_CYL, mat(0x1e88e5), 0, 0.75, 0); m.scale.set(0.7, 1.5, 0.7); obj.add(m);
          for (const y of [0.3, 1.2]) { const r = mesh(G_CYL, mat(0x0d47a1), 0, y, 0); r.scale.set(0.72, 0.08, 0.72); obj.add(r); }
          addCollider(Lv, p.x - 0.7, p.x + 0.7, p.z - 0.7, p.z + 0.7, 0, 1.5);
        } else if (ty === 'house') {
          obj = new THREE.Group(); obj.position.set(p.x, 0, p.z);
          const m = mesh(G_BOX, mat(pick([0xff8a80, 0x80d8ff, 0xffe57f])), 0, 1, 0); m.scale.set(2.2, 2, 2.2); obj.add(m);
          const roof = mesh(new THREE.ConeGeometry(1.9, 1.2, 4), mat(0xd84315), 0, 2.6, 0); roof.rotation.y = Math.PI / 4; obj.add(roof);
          const door = mesh(G_BOX, mat(0x5d4037), 0, 0.6, 1.11, false); door.scale.set(0.7, 1.2, 0.02); obj.add(door);
          addCollider(Lv, p.x - 1.1, p.x + 1.1, p.z - 1.1, p.z + 1.1, 0, 2);
        } else {
          obj = makeCar(pick([0xe53935, 0x43a047, 0x1e88e5])); obj.position.set(p.x, 0, p.z);
          addCollider(Lv, p.x - 0.9, p.x + 0.9, p.z - 1.9, p.z + 1.9, 0, 1.5);
        }
        sc.add(obj);
        spots.push({ x: p.x, z: p.z, obj, kid: null, searched: false, mark: null, ty, shakeT: rand(0, 3) });
      }
      for (let i = 0; i < 8; i++) { const p = randomFreeSpot(Lv, 20, 1.5); sc.add(makeTree(p.x, p.z, 0.8)); addCollider(Lv, p.x - 0.2, p.x + 0.2, p.z - 0.2, p.z + 0.2, 0, 2); }
      scatterCoins(Lv, 12, 19);
      const hidden = shuffle(spots.slice()).slice(0, K);
      const kids = hidden.map(s => {
        const m = randomKid(); m.visible = false; sc.add(m);
        const k = { m, spot: s, found: false, e: null, home: null }; s.kid = k; return k;
      });
      const hl = new THREE.Mesh(new THREE.RingGeometry(1.2, 1.5, 32), new THREE.MeshBasicMaterial({ color: 0xffff66, transparent: true, opacity: 0.8, side: THREE.DoubleSide }));
      hl.rotation.x = -Math.PI / 2; hl.visible = false; sc.add(hl);
      let found = 0, moveT = 0, near = null;
      Lv.spawn = { x: 0, z: 13 };
      Lv.spots = spots;
      Lv.goal = () => `🙈 Найдено ${found}/${K}`;
      const searchR = () => 2.3 + (st.reach - 1) * 2.2;
      Lv.onAction = () => {
        if (!near) { toast('Подойди ближе к укрытию 🌳'); return; }
        const s = near;
        if (s.kid) {
          const k = s.kid; s.kid = null; k.found = true; found++;
          k.m.visible = true; k.m.position.set(s.x + 1.2, 0, s.z + 1.2);
          k.e = ent(k.m, s.x + 1.4, s.z + 1.4); k.e.pos.y = 0; k.e.vel.y = 7;
          k.home = { x: -1.5 + (found - 1) * 0.6, z: 15.8 };
          SFX.good(); burst(k.e.pos, KID_COLORS, 16);
          bigMsg(found >= K ? 'Всех нашёл! 🎉' : 'Нашёл! 😄', '#7CFF6B', 900);
          if (found >= K) later(win, 800);
          if (s.mark) { sc.remove(s.mark); s.mark = null; }
        } else if (s.searched) {
          toast('Тут уже смотрел — пусто 🤷');
        } else {
          {
            s.searched = true;
            s.mark = textSprite('✖ пусто', '#ff6b6b', 'rgba(0,0,0,0.5)', 2); s.mark.position.set(s.x, 3, s.z); sc.add(s.mark);
          }
          G.time += 3; SFX.bad(); toast('Пусто! −3 сек ⏱');
        }
      };
      Lv.update = (dt) => {
        const t = G.time;
        near = null; let nd = searchR();
        for (const s of spots) {
          const dd = dist2D(s, P.pos);
          if (dd < nd && !(s.searched && !s.kid && s.mark)) { nd = dd; near = s; }
          s.obj.rotation.z = 0;
          if (s.kid) {
            s.shakeT -= dt;
            const hintR = [9, 7, 5.5][d];
            if (s.shakeT <= 0 && dd < hintR) { s.shakeT = rand(2.5, 5) * (1 + d * 0.4); s.shaking = 0.5; if (dd < hintR) SFX.giggle(); }
            if (s.shaking > 0) { s.shaking -= dt; s.obj.rotation.z = Math.sin(t * 40) * 0.06; }
          }
        }
        if (!near) for (const s of spots) { const dd = dist2D(s, P.pos); if (dd < nd) { nd = dd; near = s; } }
        hl.visible = !!near;
        if (near) { hl.position.set(near.x, 0.05, near.z); hl.material.opacity = 0.5 + Math.sin(t * 6) * 0.3; }
        for (const k of kids) {
          if (!k.found || !k.e) continue;
          const dx = k.home.x - k.e.pos.x, dz = k.home.z - k.e.pos.z, dd = Math.hypot(dx, dz);
          if (dd > 0.3) { steer(k.e, dx, dz, 4.5, dt, Lv); animKid(k.m, dt, 0.8, !k.e.onGround); }
          else { k.e.yaw = Math.PI; syncEnt(k.e, dt); k.m.rotation.y = Math.PI; animKid(k.m, dt, 0, false, 'cheer'); }
        }
        if (d === 2) {
          moveT += dt;
          if (moveT > 16) {
            moveT = 0;
            const left = kids.filter(k => !k.found);
            const free = spots.filter(s => !s.kid && dist2D(s, P.pos) > 6);
            if (left.length && free.length) {
              const k = pick(left), to = pick(free);
              k.spot.kid = null; k.spot = to; to.kid = k;
              if (to.mark) { sc.remove(to.mark); to.mark = null; to.searched = false; }
              toast('Кто-то перебежал в другое укрытие! 👀'); beep(400, 0.3, 'sine', 0.05, 900);
            }
          }
        }
      };
      return Lv;
    }
  },

  // ================= 5. ДОГОНЯШКИ =================
  {
    id: 'tag', name: 'Догоняшки', emoji: '🏃', color: '#1982c4',
    short: 'Догони и «заморозь» всех',
    desc: 'Салки-замри! Догони каждого друга и коснись его — он замрёт. Заморозь всех, пока не кончилось время.',
    how: ['Беги за друзьями и касайся их — они замирают ❄️', 'Держи 💨 для рывка (полоска выносливости внизу)', 'Друзья устают после рывка — лови момент', 'На трудном уровне друзья могут «разморозить» замерших — поторопись!'],
    build(d, st) {
      const Lv = newLevel({ sky: 0x9fdcff, timeLimit: [60, 75, 95][d] });
      const sc = Lv.scene;
      addGround(Lv, 46, canvasTex(64, (c, s) => { c.fillStyle = '#ff8a65'; c.fillRect(0, 0, s, s); c.fillStyle = '#ff7043'; c.fillRect(0, 0, s / 2, s / 2); c.fillRect(s / 2, s / 2, s / 2, s / 2); }, 12));
      const half = 18;
      addFence(Lv, half, 1.2, 0x4fc3f7);
      // горка
      addBlock(Lv, -8, -8, 1.6, 1.6, 2.6, 0xffeb3b);
      const slide = mesh(G_BOX, mat(0xff5252), -8, 1.3, -5.6); slide.scale.set(1.2, 0.15, 3.6); slide.rotation.x = -0.6; sc.add(slide);
      // песочница (низкие бортики)
      for (const [x, z, w, dd] of [[8, 5.5, 5, 0.3], [8, 10.5, 5, 0.3], [5.5, 8, 0.3, 5], [10.5, 8, 0.3, 5]]) addBlock(Lv, x, z, w, dd, 0.3, 0xa1887f);
      const sand = mesh(G_BOX, mat(0xffe0a3), 8, 0.05, 8, false); sand.scale.set(4.7, 0.1, 4.7); sc.add(sand);
      // качели
      for (const x of [6, 10]) addBlock(Lv, x, -9, 0.3, 0.3, 3, 0x795548);
      const bar = mesh(G_BOX, mat(0x795548), 8, 3, -9); bar.scale.set(4.3, 0.2, 0.2); sc.add(bar);
      // лавочки и деревья
      for (const [x, z] of [[-12, 6], [0, -13], [13, -2]]) addBlock(Lv, x, z, 2.4, 0.7, 0.5, 0x8d6e63);
      for (let i = 0; i < 6; i++) { const p = randomFreeSpot(Lv, 15, 2, [{ x: 0, z: 0, r: 4 }]); sc.add(makeTree(p.x, p.z, 1)); addCollider(Lv, p.x - 0.25, p.x + 0.25, p.z - 0.25, p.z + 0.25, 0, 3); }
      addBlock(Lv, -9, 9, 3, 3, 1.4, 0x7e57c2);
      scatterCoins(Lv, 12, 16);
      const R = [3, 5, 6][d], base = [3.5, 4.1, 4.7][d];
      const runners = [];
      for (let i = 0; i < R; i++) {
        const p = randomFreeSpot(Lv, 15, 1, [{ x: 0, z: 0, r: 7 }]);
        const m = randomKid(); sc.add(m);
        const e = ent(m, p.x, p.z); e.frozen = false; e.energy = 2; e.tired = 0; e.wt = 0; e.wx = 0; e.wz = 0; e.rescue = 0; e.ice = null;
        runners.push(e);
      }
      Lv.spawn = { x: 0, z: 0 };
      const frozenN = () => runners.filter(r => r.frozen).length;
      Lv.goal = () => `❄️ Заморожено ${frozenN()}/${R}`;
      Lv.pointer = () => {
        let best = null, bd = 1e9;
        for (const r of runners) if (!r.frozen) { const dd = dist2D(r.pos, P.pos); if (dd < bd) { bd = dd; best = r.pos; } }
        return best;
      };
      const iceM = new THREE.MeshLambertMaterial({ color: 0x9be7ff, transparent: true, opacity: 0.45, depthWrite: false });
      Lv.update = (dt) => {
        for (const r of runners) {
          if (r.frozen) {
            animKid(r.mesh, dt, 0, false, 'frozen');
            if (d === 2) {
              const helper = runners.find(o => !o.frozen && dist2D(o.pos, r.pos) < 1.3);
              if (helper) {
                r.rescue += dt;
                if (r.rescue > 0.9) {
                  r.frozen = false; r.rescue = 0; r.mesh.remove(r.ice); r.energy = 2;
                  toast('Друга разморозили! 😱'); beep(800, 0.2, 'sine', 0.05, 1600);
                }
              } else r.rescue = Math.max(0, r.rescue - dt);
            }
            continue;
          }
          const dx = r.pos.x - P.pos.x, dz = r.pos.z - P.pos.z, dd = Math.hypot(dx, dz);
          if (dd < 1.0 + 0.35 * st.reach && Math.abs(P.pos.y - r.pos.y) < 1.5) {
            r.frozen = true; r.vel.set(0, 0, 0);
            r.ice = mesh(G_BOX, iceM, 0, 0.9, 0, false); r.ice.scale.set(1.1, 1.9, 0.9); r.mesh.add(r.ice);
            SFX.good(); burst(r.pos, [0x9be7ff, 0xffffff], 14);
            const f = frozenN();
            if (f >= R) win(); else toast(`Попался! ❄️ Осталось ${R - f}`);
            continue;
          }
          let spd = base, mx, mz;
          if (r.tired > 0) { r.tired -= dt; spd *= 0.6; }
          if (dd < 9) {
            mx = dx / (dd || 1); mz = dz / (dd || 1);
            if (dd < 4.5 && r.tired <= 0 && r.energy > 0) { spd *= 1.35; r.energy -= dt; if (r.energy <= 0) { r.tired = 1.6; } }
            // отталкиваться от забора
            const wall = half - 2.5;
            if (r.pos.x > wall) mx -= (r.pos.x - wall) * 0.9; if (r.pos.x < -wall) mx += (-wall - r.pos.x) * 0.9;
            if (r.pos.z > wall) mz -= (r.pos.z - wall) * 0.9; if (r.pos.z < -wall) mz += (-wall - r.pos.z) * 0.9;
            if (r.bumped) { const tx = -mz, tz = mx; mx = mx * 0.3 + tx; mz = mz * 0.3 + tz; }
          } else {
            r.energy = Math.min(2, r.energy + dt * 0.5);
            const fr = d === 2 ? runners.find(o => o.frozen) : null;
            if (fr && dd > 6) { mx = fr.pos.x - r.pos.x; mz = fr.pos.z - r.pos.z; spd *= 0.9; }
            else {
              r.wt -= dt;
              if (r.wt <= 0) { r.wt = rand(1.5, 3); const a = rand(0, 6.28); r.wx = Math.cos(a); r.wz = Math.sin(a); }
              mx = r.wx - r.pos.x * 0.04; mz = r.wz - r.pos.z * 0.04; spd *= 0.5;
            }
          }
          steer(r, mx, mz, spd, dt, Lv, 6);
          animKid(r.mesh, dt, spd / 6, false);
        }
      };
      return Lv;
    }
  },

  // ================= 6. АМОГУС =================
  {
    id: 'among', name: 'Амогус', emoji: '👾', color: '#c51111',
    short: 'Выполни задания, не попадись предателю',
    desc: 'Ты на космическом корабле, а среди экипажа — предатель! Почини корабль, выполнив все задания, и нажми аварийную кнопку.',
    how: ['Иди к жёлтым пультам с «!» и держи 🔧, пока шкала не заполнится', 'Красный — предатель! Если заметит тебя — побежит следом', 'Убегай через другие двери, предатель не видит сквозь стены далеко', 'Когда все задания готовы — беги к красной кнопке в кафетерии и жми 🔧', 'На сложных уровнях предатель лазит по вентиляции и выключает свет'],
    build(d, st) {
      const Lv = newLevel({ sky: 0x05070f, fog: [0x05070f, 26, 60], timeLimit: [130, 150, 170][d], actionLabel: '🔧', music: 'space', camOffset: V3(0, 12, 8.5) });
      const sc = Lv.scene;
      sc.userData.hemi.intensity = 0.75;
      const floorT = canvasTex(64, (c, s) => { c.fillStyle = '#8a94a6'; c.fillRect(0, 0, s, s); c.strokeStyle = '#6b7385'; c.lineWidth = 3; c.strokeRect(1, 1, s - 2, s - 2); c.fillStyle = '#9aa4b6'; c.fillRect(8, 8, 6, 6); }, 22);
      addGround(Lv, 44, floorT);
      const RW = 14, RD = 12, DOOR = 3.6, WH = 2.2, T = 0.4;
      const wallM = mat(0xc8d1e0);
      const rooms = [];
      const names = [['Реактор', 'Электрика', 'Склад'], ['Двигатель', 'Кафетерий', 'Медпункт'], ['Навигация', 'Оружие', 'Админ']];
      for (let j = 0; j < 3; j++) for (let i = 0; i < 3; i++) {
        const cx = (i - 1) * RW, cz = (j - 1) * RD;
        rooms.push({ i, j, cx, cz, name: names[j][i] });
        const lab = textSprite(names[j][i], '#bfe9ff', null, 3); lab.position.set(cx, 3.2, cz - RD / 2 + 1); sc.add(lab);
      }
      const W = RW * 1.5, D = RD * 1.5;
      addBlock(Lv, 0, -D - T / 2, W * 2 + T * 2, T, WH, wallM); addBlock(Lv, 0, D + T / 2, W * 2 + T * 2, T, WH, wallM);
      addBlock(Lv, -W - T / 2, 0, T, D * 2, WH, wallM); addBlock(Lv, W + T / 2, 0, T, D * 2, WH, wallM);
      for (const x0 of [-RW / 2, RW / 2]) for (let j = 0; j < 3; j++) {
        const zc = (j - 1) * RD, z1 = zc - RD / 2, z2 = zc + RD / 2;
        const a = z1, b = zc - DOOR / 2, c2 = zc + DOOR / 2;
        addBlock(Lv, x0, (a + b) / 2, T, b - a, WH, wallM); addBlock(Lv, x0, (c2 + z2) / 2, T, z2 - c2, WH, wallM);
      }
      for (const z0 of [-RD / 2, RD / 2]) for (let i = 0; i < 3; i++) {
        const xc = (i - 1) * RW, x1 = xc - RW / 2, x2 = xc + RW / 2;
        const a = x1, b = xc - DOOR / 2, c2 = xc + DOOR / 2;
        addBlock(Lv, (a + b) / 2, z0, b - a, T, WH, wallM); addBlock(Lv, (c2 + x2) / 2, z0, x2 - c2, T, WH, wallM);
      }
      // стол с аварийной кнопкой
      const table = mesh(G_CYL, mat(0x90a4ae), 0, 0.45, 0); table.scale.set(1.3, 0.9, 1.3); sc.add(table);
      addCollider(Lv, -1.1, 1.1, -1.1, 1.1, 0, 0.9);
      const btn = mesh(G_CYL, mat(0xff1744, { emissive: 0x700000 }), 0, 1.0, 0); btn.scale.set(0.4, 0.2, 0.4); sc.add(btn);
      const glass = mesh(G_SPH, new THREE.MeshLambertMaterial({ color: 0xbfe9ff, transparent: true, opacity: 0.35 }), 0, 1.0, 0, false); glass.scale.set(0.5, 0.4, 0.5); sc.add(glass);
      // ящики
      for (const r of rooms) if (r.name !== 'Кафетерий') {
        const sx = pick([-1, 1]), sz = pick([-1, 1]);
        addBlock(Lv, r.cx + sx * (RW / 2 - 1.4), r.cz + sz * (RD / 2 - 1.4), 1.4, 1.4, 1.1, 0x6d7a8a);
      }
      const roomOf = (p) => {
        const i = clamp(Math.floor((p.x + W) / RW), 0, 2), j = clamp(Math.floor((p.z + D) / RD), 0, 2);
        return rooms[j * 3 + i];
      };
      // навигация между комнатами через двери
      const navTarget = (from, to) => {
        const a = roomOf(from), b = roomOf(to);
        if (a === b) return to;
        let ni = a.i, nj = a.j;
        if (a.i !== b.i) ni += Math.sign(b.i - a.i); else nj += Math.sign(b.j - a.j);
        const n = rooms[nj * 3 + ni];
        const door = { x: (a.cx + n.cx) / 2, z: (a.cz + n.cz) / 2 };
        const onAxisX = ni !== a.i;
        const inline = onAxisX ? Math.abs(from.z - door.z) < DOOR / 2 - 0.5 : Math.abs(from.x - door.x) < DOOR / 2 - 0.5;
        const dd = Math.hypot(from.x - door.x, from.z - door.z);
        if (inline && dd < 1.5) return { x: n.cx, z: n.cz };
        return onAxisX ? { x: door.x + (a.cx - door.x) * (inline ? -0.3 : 0.12), z: door.z } : { x: door.x, z: door.z + (a.cz - door.z) * (inline ? -0.3 : 0.12) };
      };
      // задания
      const TN = [4, 6, 8][d];
      const tasks = [];
      const taskRooms = shuffle(rooms.filter(r => r.name !== 'Кафетерий'));
      for (let k = 0; k < TN; k++) {
        const r = taskRooms[k % taskRooms.length];
        const x = r.cx + rand(-4, 4), z = r.cz + (k >= 8 ? 2 : rand(-3, 3));
        const g = new THREE.Group(); g.position.set(x, 0, z);
        const b = mesh(G_BOX, mat(0x455a64), 0, 0.55, 0); b.scale.set(1, 1.1, 0.6); g.add(b);
        const scr = mesh(G_BOX, mat(0xffd600, { emissive: 0x806b00 }), 0, 1.0, 0.31, false); scr.scale.set(0.8, 0.4, 0.02); g.add(scr);
        const ex = textSprite('❗ ' + r.name, '#ffe14d', 'rgba(0,0,0,0.5)', 2.4); ex.position.y = 2.2; g.add(ex);
        sc.add(g); addCollider(Lv, x - 0.5, x + 0.5, z - 0.3, z + 0.3, 0, 1.1);
        tasks.push({ g, scr, ex, x, z, p: 0, done: false });
      }
      // экипаж
      const crew = [];
      for (const c of [0x132ed1, 0x117f2d, 0xf5f557, 0xef7d0d, 0x6b2fbb, 0x38fedc].slice(0, 4)) {
        const m = makeCrewmate(c); sc.add(m);
        const r = pick(rooms); const e = ent(m, r.cx + rand(-3, 3), r.cz + rand(-3, 3)); e.r = 0.45; e.goal = null; crew.push(e);
      }
      const impostors = [];
      for (let k = 0; k < [1, 1, 2][d]; k++) {
        const m = makeCrewmate(0xc51111); sc.add(m);
        const r = rooms[k === 0 ? 0 : 8];
        const e = ent(m, r.cx, r.cz); e.r = 0.45; e.goal = null; e.pause = 3; e.chasing = false; impostors.push(e);
      }
      const isp = [3.2, 3.7, 4.2][d], sight = [6.5, 7.5, 8.5][d];
      let doneN = 0, ventT = 0, lightsT = 0, lightsOff = 0;
      Lv.spawn = { x: 0, z: 3 };
      Lv.goal = () => doneN < TN ? `🔧 Задания ${doneN}/${TN}${lightsOff > 0 ? ' &nbsp;💡 Свет выключен!' : ''}` : '🚨 Жми аварийную кнопку в кафетерии!';
      Lv.pointer = () => {
        if (doneN >= TN) return { x: 0, z: 0 };
        let best = null, bd = 1e9;
        for (const t of tasks) if (!t.done) { const dd = dist2D(t, P.pos); if (dd < bd) { bd = dd; best = t; } }
        return best ? navTarget(P.pos, best) : null;
      };
      Lv.onAction = () => {
        if (doneN >= TN && dist2D(P.pos, { x: 0, z: 0 }) < 2.6) {
          G.progress = null; btn.position.y = 0.95; beep(880, 0.6, 'square', 0.08, 440);
          bigMsg('🚨 СОБРАНИЕ! Предатель пойман!', '#ff6b6b', 1500);
          later(win, 900);
        } else if (doneN >= TN) toast('Беги к красной кнопке в центре 🚨');
      };
      Lv.onRespawn = () => {
        for (const im of impostors) { const r = pick(rooms.filter(r => r.name !== 'Кафетерий')); im.pos.set(r.cx, 0, r.cz); im.pause = 2.5; }
      };
      Lv.update = (dt) => {
        const t = G.time;
        // задания
        let active = null;
        for (const tk of tasks) {
          if (tk.done) continue;
          tk.ex.position.y = 2.2 + Math.sin(t * 4) * 0.1;
          if (dist2D(tk, P.pos) < 1.7 * st.reach) active = tk;
        }
        if (active && input.actionHeld) {
          active.p += dt / 2.4;
          if (Math.floor(t * 8) % 2 === 0) beep(600 + active.p * 600, 0.04, 'square', 0.02);
          if (active.p >= 1) {
            active.done = true; doneN++; active.g.remove(active.ex);
            active.scr.material = mat(0x00e676, { emissive: 0x006b30 });
            SFX.good(); burst(P.pos, [0x00e676, 0xffffff], 12);
            toast(doneN >= TN ? 'Все задания готовы! Беги к кнопке 🚨' : `Задание выполнено! ✅ ${doneN}/${TN}`);
          }
        }
        G.progress = active ? active.p : null;
        btn.material.emissive.setHex(doneN >= TN && Math.floor(t * 4) % 2 ? 0xff0000 : 0x700000);
        // экипаж бродит
        for (const c of crew) {
          if (!c.goal || dist2D(c.pos, c.goal) < 1) { const r = pick(rooms); c.goal = { x: r.cx + rand(-3, 3), z: r.cz + rand(-3, 3) }; }
          const nt = navTarget(c.pos, c.goal);
          steer(c, nt.x - c.pos.x, nt.z - c.pos.z, 2.2, dt, Lv); animKid(c.mesh, dt, 0.5, false);
          if (c.bumped && Math.random() < 0.02) c.goal = null;
        }
        // предатели
        for (const im of impostors) {
          if (im.pause > 0) { im.pause -= dt; steer(im, 0, 0, 0, dt, Lv, 20); continue; }
          const dd = dist2D(im.pos, P.pos);
          const sameRoom = roomOf(im.pos) === roomOf(P.pos);
          const sees = dd < sight && (sameRoom || dd < 3.5) && lightsOff <= 0 || dd < 2.5;
          if (sees && !im.chasing) { im.chasing = true; beep(150, 0.4, 'sawtooth', 0.06, 300); }
          if (!sees && dd > sight * 1.6) im.chasing = false;
          let tg;
          if (im.chasing) tg = navTarget(im.pos, P.pos);
          else {
            if (!im.goal || dist2D(im.pos, im.goal) < 1) { const r = pick(rooms); im.goal = { x: r.cx + rand(-3, 3), z: r.cz + rand(-3, 3) }; }
            tg = navTarget(im.pos, im.goal);
          }
          steer(im, tg.x - im.pos.x, tg.z - im.pos.z, im.chasing ? isp : isp * 0.6, dt, Lv);
          animKid(im.mesh, dt, 0.7, false);
          if (dd < 0.95 && P.inv <= 0) {
            bigMsg('Предатель поймал! 😱', '#ff4b4b', 1000);
            hurt(true, 'Тебя вернули в кафетерий');
            im.chasing = false;
          }
        }
        // вентиляция
        if (d >= 1) {
          ventT += dt;
          if (ventT > [99, 15, 11][d]) {
            ventT = 0;
            const im = pick(impostors);
            if (!im.chasing) {
              const pr = roomOf(P.pos);
              const r = pick(rooms.filter(r => r !== pr && r.name !== 'Кафетерий'));
              burst(im.pos, [0x777777], 8);
              im.pos.set(r.cx + rand(-2, 2), 0, r.cz + rand(-2, 2)); im.goal = null;
              burst(im.pos, [0x777777], 8); toast('Кто-то пролез в вентиляцию... 👀');
            }
          }
        }
        // свет
        if (d === 2) {
          lightsT += dt;
          if (lightsT > 26) { lightsT = 0; lightsOff = 7; toast('Предатель выключил свет! 💡'); }
          if (lightsOff > 0) lightsOff -= dt;
          const near = lightsOff > 0 ? 3 : 26, far = lightsOff > 0 ? 10 : 60;
          sc.fog.near += (near - sc.fog.near) * Math.min(1, dt * 3); sc.fog.far += (far - sc.fog.far) * Math.min(1, dt * 3);
        }
      };
      return Lv;
    }
  },

  // ================= 7. ЧЕЛОВЕК-ПАУК =================
  {
    id: 'spider', name: 'Человек-паук', emoji: '🕷', color: '#d61f26',
    short: 'Прыгай по крышам и поймай злодея',
    desc: 'Ты надел костюм Человека-паука! Прыгай по крышам небоскрёбов, лети на паутине и поймай злодея на последней крыше.',
    how: ['Маленькие пропасти — перепрыгивай ⬆️', '🕸 — выстрелить паутиной и долететь до следующей крыши', 'Паутина спасает даже в падении!', 'Упадёшь вниз — потеряешь жизнь и вернёшься на последнюю крышу', 'На последней крыше поймай злодея — просто догони его'],
    build(d, st) {
      const Lv = newLevel({ sky: 0x8ec9ff, fog: [0x8ec9ff, 45, 130], floor: false, killY: 4, timeLimit: [100, 120, 140][d], actionLabel: '🕸', costume: 'spider', camOffset: V3(0, 7.5, 11), lookAhead: 3 });
      const sc = Lv.scene;
      addGround(Lv, 400, noiseTex('#6b6f75', ['#5e6268', '#777b81'], 60));
      const n = [10, 14, 18][d];
      const roofs = [];
      let px = 0, pz = 0, ph = 10, pw = 8, pd = 8;
      for (let i = 0; i < n; i++) {
        let w = i === 0 ? 8 : i === n - 1 ? 10 : rand(5, 8), dd = i === 0 ? 8 : i === n - 1 ? 10 : rand(5, 8), h, x, z;
        if (i === 0) { x = 0; z = 0; h = 10; }
        else {
          const big = (i % 3 === 2) || (d === 2 && i % 4 === 1);
          const gap = big ? rand(7, 10) : rand(1.6, 2.4 + d * 0.25);
          h = clamp(ph + (big ? rand(-1.5, 2.5) : rand(-1.5, 0.6)), 8, 15);
          z = pz - pd / 2 - gap - dd / 2;
          x = clamp(px + rand(-3, 3), -8, 8);
        }
        const m = new THREE.MeshLambertMaterial({ map: windowTex(pick(['#7d8fa3', '#a38b7d', '#8aa37d', '#9a8fb0', '#b0a08f']), '#2f3e55') });
        m.map.repeat.set(Math.max(1, Math.round(w / 2)), Math.round(h / 2));
        const c = addBlock(Lv, x, z, w, dd, h, m, 0, { roof: i });
        const rim = mesh(G_BOX, mat(0x555a60), x, h + 0.05, z, false); rim.scale.set(w + 0.2, 0.1, dd + 0.2); sc.add(rim);
        c.rim = rim;
        if (i > 0 && i < n - 1) {
          if (Math.random() < 0.6) addCoin(Lv, x, h, z);
          if (Math.random() < 0.4) addCoin(Lv, x + 1.2, h, z - 1);
        }
        roofs.push(c);
        px = x; pz = z; ph = h; pw = w; pd = dd;
      }
      // движущиеся крыши
      const movers = d === 2 ? roofs.filter((r, i) => i > 1 && i < n - 1 && i % 4 === 3) : [];
      movers.forEach(r => { r.base = r.maxY; r.ph = rand(0, 6); });
      // далёкие здания-декор
      for (let i = 0; i < 40; i++) {
        const side = i % 2 ? 1 : -1, x = side * rand(18, 40), z = rand(pz - 20, 30), w = rand(5, 10), h = rand(8, 30);
        const m = new THREE.MeshLambertMaterial({ map: windowTex(pick(['#6d7f93', '#93806d', '#7a937a']), '#2a3446') });
        m.map.repeat.set(Math.round(w / 2), Math.round(h / 2));
        const b = mesh(G_BOX, m, x, h / 2, z, false); b.scale.set(w, h, w); sc.add(b);
      }
      // злодей
      const last = roofs[n - 1];
      const vm = makeKid({ skin: 0x6dbb3f, shirt: 0x6a1b9a, pants: 0x2e7d32, hairStyle: 'none', eyes: 0xffeb3b, height: 1.1 });
      sc.add(vm);
      const villain = ent(vm, (last.minX + last.maxX) / 2, (last.minZ + last.maxZ) / 2, last.maxY);
      villain.wt = 0; villain.dx = 0; villain.dz = 0;
      const vLab = textSprite('Злодей 😈', '#c6ff5c', 'rgba(0,0,0,0.5)', 2.2); vLab.position.y = 2.6; vm.add(vLab);
      // паутина
      const lineGeo = new THREE.BufferGeometry().setFromPoints([V3(0, 0, 0), V3(0, 1, 0)]);
      const web = new THREE.Line(lineGeo, new THREE.LineBasicMaterial({ color: 0xffffff }));
      web.visible = false; web.frustumCulled = false; sc.add(web);
      let zip = null, cd = 0, lastRoof = 0;
      Lv.spawn = { x: 0, y: 10, z: 0 };
      Lv.goal = () => lastRoof < n - 1 ? `🏙 Крыша ${lastRoof + 1}/${n}` : '😈 Поймай злодея!';
      Lv.pointer = () => {
        const r = roofs[Math.min(n - 1, lastRoof + 1)];
        if (lastRoof >= n - 1) return villain.pos;
        return { x: (r.minX + r.maxX) / 2, z: (r.minZ + r.maxZ) / 2 };
      };
      Lv.onLand = (g) => {
        if (g && g.roof !== undefined) {
          if (g.roof > lastRoof) { lastRoof = g.roof; if (g.roof === n - 1) bigMsg('Поймай злодея! 😈', '#c6ff5c', 1200); }
          if (!movers.includes(g)) Lv.checkpoint = { x: (g.minX + g.maxX) / 2, y: g.maxY, z: (g.minZ + g.maxZ) / 2 };
        }
      };
      Lv.onRespawn = () => { zip = null; web.visible = false; P.locked = false; };
      Lv.onAction = () => {
        if (zip || cd > 0) return;
        let ti = lastRoof + 1;
        if (P.ground && P.ground.roof !== undefined && P.ground.roof >= ti) ti = P.ground.roof + 1;
        if (ti >= n) { toast('Ты уже на последней крыше! Лови злодея'); return; }
        // если падаем — вернуться на ближайшую крышу
        const target = roofs[ti];
        const to = V3(clamp(P.pos.x, target.minX + 1, target.maxX - 1), target.maxY, clamp(P.pos.z, target.minZ + 1, target.maxZ - 1));
        let dist = to.distanceTo(P.pos);
        let tgt = target;
        if (dist > 28) {
          const back = roofs[lastRoof];
          tgt = back; to.set((back.minX + back.maxX) / 2, back.maxY, (back.minZ + back.maxZ) / 2); dist = to.distanceTo(P.pos);
          if (dist > 28) { toast('Слишком далеко для паутины!'); return; }
        }
        const from = P.pos.clone();
        const ctrl = from.clone().lerp(to, 0.5); ctrl.y = Math.max(from.y, to.y) + 3 + dist * 0.12;
        zip = { from, to, ctrl, t: 0, dur: clamp(dist / 17, 0.45, 1.3), anchor: V3(to.x, to.y + 9, to.z - 2), tgt };
        P.locked = true; P.vel.set(0, 0, 0); cd = 0.5; SFX.web();
      };
      Lv.update = (dt) => {
        cd -= dt;
        for (const r of movers) {
          const ny = r.base + Math.sin(G.time * 1.3 + r.ph) * 2.5;
          r.dy = ny - r.maxY; r.maxY = ny; syncColliderMesh(r);
          r.rim.position.y = r.maxY + 0.05;
        }
        if (zip) {
          zip.t += dt / zip.dur;
          const k = Math.min(1, zip.t), a = 1 - k;
          P.pos.set(
            a * a * zip.from.x + 2 * a * k * zip.ctrl.x + k * k * zip.to.x,
            a * a * zip.from.y + 2 * a * k * zip.ctrl.y + k * k * zip.to.y + 0.05,
            a * a * zip.from.z + 2 * a * k * zip.ctrl.z + k * k * zip.to.z);
          if (zip.tgt.base !== undefined) zip.to.y = zip.tgt.maxY;
          const pts = web.geometry.attributes.position;
          pts.setXYZ(0, P.pos.x, P.pos.y + 1.6, P.pos.z); pts.setXYZ(1, zip.anchor.x, zip.anchor.y, zip.anchor.z); pts.needsUpdate = true;
          web.visible = true;
          P.mesh.userData.arms[1].rotation.x = -2.8;
          if (k >= 1) { zip = null; web.visible = false; P.locked = false; P.vel.set(0, 0, 0); P.onGround = false; P.pos.y += 0.1; }
        }
        // злодей
        const onLast = lastRoof === n - 1;
        const dxv = villain.pos.x - P.pos.x, dzv = villain.pos.z - P.pos.z, dv = Math.hypot(dxv, dzv);
        if (onLast) {
          let mx = dxv / (dv || 1), mz = dzv / (dv || 1);
          const cx = (last.minX + last.maxX) / 2, cz = (last.minZ + last.maxZ) / 2;
          if (villain.pos.x > last.maxX - 1.5 || villain.pos.x < last.minX + 1.5 || villain.pos.z > last.maxZ - 1.5 || villain.pos.z < last.minZ + 1.5) {
            mx = mx * 0.2 + (cx - villain.pos.x) * 0.3 - mz * 0.8; mz = mz * 0.2 + (cz - villain.pos.z) * 0.3 + mx * 0.8;
          }
          steer(villain, mx, mz, dv < 5 ? 3.6 + d * 0.5 : 1.5, dt, Lv, 6);
          villain.pos.x = clamp(villain.pos.x, last.minX + 0.5, last.maxX - 0.5); villain.pos.z = clamp(villain.pos.z, last.minZ + 0.5, last.maxZ - 0.5);
          villain.pos.y = last.maxY; villain.mesh.position.copy(villain.pos);
          animKid(vm, dt, 0.8, false);
          if (dv < 1.0 + 0.3 * st.reach && Math.abs(P.pos.y - villain.pos.y) < 1.2) {
            bigMsg('Злодей пойман! 🕸', '#ffffff', 1200); burst(villain.pos, [0xffffff, 0xd61f26], 30); win();
          }
        } else {
          villain.mesh.position.copy(villain.pos); villain.mesh.rotation.y = Math.atan2(-dxv, -dzv);
          animKid(vm, dt, 0, false, 'cheer');
        }
      };
      return Lv;
    }
  },

  // ================= 8. ПОЛ — ЭТО ЛАВА =================
  {
    id: 'lava', name: 'Пол — это лава!', emoji: '🌋', color: '#ff7b00',
    short: 'Прыгай по мебели до двери',
    desc: 'Внимание: пол превратился в лаву! Прыгай по диванам, столам и подушкам, чтобы добраться до двери.',
    how: ['Прыгай ⬆️ с одной мебели на другую', 'Коснёшься пола — потеряешь жизнь', 'Розовые подушки тонут, если стоять на них долго!', 'Скейтборды на трудном уровне катаются туда-сюда', 'Доберись до зелёной двери в конце комнаты'],
    build(d, st) {
      const Lv = newLevel({ sky: 0x2b1408, floor: false, killY: -3, timeLimit: [70, 85, 100][d], camOffset: V3(0, 8, 9), lookAhead: 3 });
      Lv.lavaY = 0;
      const sc = Lv.scene;
      sc.userData.hemi.intensity = 0.7;
      const lavaTex = canvasTex(128, (c, s) => {
        c.fillStyle = '#ff5a00'; c.fillRect(0, 0, s, s);
        for (let i = 0; i < 40; i++) { c.fillStyle = pick(['#ffb300', '#ff7b00', '#ff3d00', '#ffd54f']); c.beginPath(); c.arc(Math.random() * s, Math.random() * s, 4 + Math.random() * 14, 0, 7); c.fill(); }
      }, 8, 30);
      const lava = new THREE.Mesh(new THREE.PlaneGeometry(18, 100), new THREE.MeshBasicMaterial({ map: lavaTex }));
      lava.rotation.x = -Math.PI / 2; lava.position.set(0, 0, -29); sc.add(lava);
      const glow = new THREE.PointLight(0xff6a00, 1.2, 30); glow.position.set(0, 3, -20); sc.add(glow);
      const wallM = new THREE.MeshLambertMaterial({ map: canvasTex(64, (c, s) => { c.fillStyle = '#f3e5ab'; c.fillRect(0, 0, s, s); c.fillStyle = '#e6d28f'; for (let x = 0; x < s; x += 16) c.fillRect(x, 0, 6, s); }, 20, 2) });
      addBlock(Lv, -9, -27, 1, 96, 6, wallM); addBlock(Lv, 9, -27, 1, 96, 6, wallM);
      addBlock(Lv, 0, 20.5, 18, 1, 6, wallM);
      // старт — ковёр-диван
      const start = addBlock(Lv, 0, 9, 5, 4, 1.0, 0x5d4037, 0, { safe: true });
      const plats = [start];
      let z = 9 - 2, prevH = 1.0, x = 0;
      const M = [12, 16, 21][d];
      const movers = [], sinkers = [];
      for (let i = 0; i < M; i++) {
        const type = (d >= 1 && i % 3 === 1) ? 'cushion' : (d === 2 && i % 5 === 3) ? 'skate' : pick(['sofa', 'table', 'chair', 'books', 'box']);
        let w, dd, h, col;
        if (type === 'sofa') { w = 3; dd = 1.4; h = 0.9; col = pick([0x1565c0, 0x6a1b9a, 0x2e7d32]); }
        else if (type === 'table') { w = 2; dd = 2; h = 1.2; col = 0x8d6e63; }
        else if (type === 'chair') { w = 1.1; dd = 1.1; h = 0.9; col = 0xa1887f; }
        else if (type === 'books') { w = 1.2; dd = 1.2; h = rand(0.6, 1.8); col = pick([0xe53935, 0x1e88e5, 0xfdd835]); }
        else if (type === 'cushion') { w = 1.5; dd = 1.5; h = 0.55; col = 0xf48fb1; }
        else if (type === 'skate') { w = 1.6; dd = 1.6; h = 0.5; col = 0x26c6da; }
        else { w = 1.4; dd = 1.4; h = 1.0; col = 0xffb74d; }
        if (type === 'books' || type === 'box' || type === 'table') h = clamp(prevH + rand(-0.5, 0.75), 0.6, 2.2);
        const gap = rand(1.0, 1.7 + d * 0.25);
        z -= gap + dd / 2;
        x = clamp(x + rand(-2.2, 2.2), -6, 6);
        const c = addBlock(Lv, x, z, w, dd, h, col, 0, { plat: true, safe: type !== 'cushion' && type !== 'skate' });
        if (type === 'sofa') { const back = mesh(G_BOX, mat(col), x, h + 0.35, z - dd / 2 + 0.15); back.scale.set(w, 0.7, 0.3); sc.add(back); c.extra = back; }
        if (type === 'cushion') { c.sink = 0; c.base = h; c.timer = 0; sinkers.push(c); }
        if (type === 'skate') { c.ph = rand(0, 6); c.x0 = x; movers.push(c); }
        if (Math.random() < 0.5) addCoin(Lv, x, h, z);
        plats.push(c);
        z -= dd / 2; prevH = h;
      }
      // финиш — дверь
      z -= 1.6 + 2;
      const fin = addBlock(Lv, x, z, 4, 4, Math.max(0.8, prevH), 0x66bb6a, 0, { safe: true, finish: true });
      const door = mesh(G_BOX, mat(0x6d4c41), x, fin.maxY + 1.3, z - 1.8); door.scale.set(1.6, 2.6, 0.2); sc.add(door);
      const knob = mesh(G_SPH, mat(0xffd54f), x + 0.55, fin.maxY + 1.2, z - 1.65); knob.scale.setScalar(0.1); sc.add(knob);
      const exitS = textSprite('ВЫХОД 🚪', '#7CFF6B', 'rgba(0,0,0,0.5)', 2.5); exitS.position.set(x, fin.maxY + 3.2, z - 1.6); sc.add(exitS);
      addBlock(Lv, 0, z - 3, 18, 1, 6, wallM);
      Lv.spawn = { x: 0, y: 1.0, z: 9.5 };
      const total = 9 - z;
      Lv.goal = () => `🔥 До двери ${Math.max(0, Math.round((P.pos.z - z)))} м`;
      Lv.pointer = () => ({ x: fin.mesh.position.x, z: fin.mesh.position.z });
      Lv.onLand = (g) => {
        if (!g) return;
        if (g.finish) { burst(P.pos, KID_COLORS, 30); win(); return; }
        if (g.safe) Lv.checkpoint = { x: (g.minX + g.maxX) / 2, y: g.maxY, z: (g.minZ + g.maxZ) / 2 };
      };
      Lv.update = (dt) => {
        lavaTex.offset.y += dt * 0.05; lavaTex.offset.x = Math.sin(G.time * 0.5) * 0.05;
        glow.position.z = P.pos.z - 4;
        for (const c of movers) {
          const nx = c.x0 + Math.sin(G.time * 1.4 + c.ph) * 3;
          moveCollider(c, nx - (c.minX + c.maxX) / 2, 0, 0);
        }
        for (const c of sinkers) {
          const on = P.onGround && P.ground === c;
          if (on) c.timer += dt; else c.timer = Math.max(0, c.timer - dt * 0.5);
          let target = c.base;
          if (c.timer > 0.6) target = 0.02;
          const ny = c.maxY + (target - c.maxY) * Math.min(1, dt * (target < c.maxY ? 0.9 : 1.5));
          if (Math.abs(ny - c.maxY) > 0.0001) { c.maxY = ny; c.dy = 0; syncColliderMesh(c); if (on) P.pos.y = c.maxY; }
          c.mesh.rotation.z = on ? Math.sin(G.time * 25) * 0.03 : 0;
        }
      };
      return Lv;
    }
  },

  // ================= 9. ФУТБОЛ =================
  {
    id: 'football', name: 'Футбол', emoji: '⚽', color: '#2e7d32',
    short: 'Забей голы вратарю',
    desc: 'Финал чемпионата двора! Веди мяч, обыгрывай защитников и забивай голы хитрому вратарю.',
    how: ['Подбеги к мячу — будешь вести его перед собой', '⚽ — сильный удар туда, куда смотрит герой', 'Вратарь двигается за мячом — бей в угол!', 'Защитники пытаются отобрать мяч', 'Забей нужное число голов до конца матча'],
    build(d, st) {
      const Lv = newLevel({ sky: 0x8fd3ff, timeLimit: [90, 100, 115][d], actionLabel: '⚽', camOffset: V3(0, 12, 10.5), lookAhead: 2 });
      const sc = Lv.scene;
      const HX = 14, HZ = 22, GW = 3.6;
      const pitch = canvasTex(256, (c, s) => {
        for (let i = 0; i < 10; i++) { c.fillStyle = i % 2 ? '#43a047' : '#4caf50'; c.fillRect(0, i * s / 10, s, s / 10); }
        c.strokeStyle = '#ffffff'; c.lineWidth = 3;
        c.strokeRect(8, 8, s - 16, s - 16);
        c.beginPath(); c.moveTo(8, s / 2); c.lineTo(s - 8, s / 2); c.stroke();
        c.beginPath(); c.arc(s / 2, s / 2, 30, 0, 7); c.stroke();
        c.strokeRect(s / 2 - 60, 8, 120, 45); c.strokeRect(s / 2 - 60, s - 53, 120, 45);
      }, 1);
      const g = mesh(new THREE.PlaneGeometry(HX * 2 + 1, HZ * 2 + 1), new THREE.MeshLambertMaterial({ map: pitch }), 0, 0.01, 0, false);
      g.rotation.x = -Math.PI / 2; sc.add(g);
      addGround(Lv, 120, noiseTex('#3b8f3b', ['#348034', '#45a045']), 0xffffff).position.y = -0.01;
      const bM = mat(0xffffff);
      addBlock(Lv, -HX - 0.3, 0, 0.6, HZ * 2, 0.8, 0x1565c0); addBlock(Lv, HX + 0.3, 0, 0.6, HZ * 2, 0.8, 0x1565c0);
      addBlock(Lv, 0, HZ + 0.3, HX * 2 + 1.2, 0.6, 0.8, 0x1565c0);
      addBlock(Lv, -(HX + GW) / 2 - 0.3, -HZ - 0.3, HX - GW + 0.6, 0.6, 0.8, 0x1565c0);
      addBlock(Lv, (HX + GW) / 2 + 0.3, -HZ - 0.3, HX - GW + 0.6, 0.6, 0.8, 0x1565c0);
      // ворота
      for (const sx of [-GW, GW]) { addBlock(Lv, sx, -HZ, 0.2, 0.2, 2.4, bM); }
      const cross = mesh(G_BOX, bM, 0, 2.4, -HZ); cross.scale.set(GW * 2 + 0.2, 0.2, 0.2); sc.add(cross);
      const netM = new THREE.MeshLambertMaterial({ color: 0xffffff, transparent: true, opacity: 0.35, side: THREE.DoubleSide });
      addBlock(Lv, 0, -HZ - 2.1, GW * 2, 0.1, 2.4, netM);
      addBlock(Lv, -GW, -HZ - 1.05, 0.1, 2, 2.4, netM); addBlock(Lv, GW, -HZ - 1.05, 0.1, 2, 2.4, netM);
      // трибуны
      for (const sx of [-1, 1]) for (let r = 0; r < 3; r++) {
        const tri = mesh(G_BOX, mat([0xe53935, 0xfdd835, 0x1e88e5][r]), sx * (HX + 3 + r * 1.2), 0.5 + r * 0.8, 0); tri.scale.set(1.2, 1 + r * 1.6, HZ * 2); sc.add(tri);
        for (let k = 0; k < 5; k++) { const fan = randomKid(); fan.traverse(o => { o.castShadow = false; }); fan.scale.setScalar(0.8); fan.position.set(sx * (HX + 3 + r * 1.2), 1 + r * 1.6, rand(-HZ + 2, HZ - 2)); fan.rotation.y = -sx * Math.PI / 2; fan.userData.fan = true; sc.add(fan); }
      }
      // мяч
      const ballTex = canvasTex(128, (c, s) => { c.fillStyle = '#fff'; c.fillRect(0, 0, s, s); c.fillStyle = '#111'; for (let i = 0; i < 4; i++) for (let j = 0; j < 4; j++) if ((i + j) % 2 === 0) { c.beginPath(); c.arc(i * s / 4 + s / 8, j * s / 4 + s / 8, s / 12, 0, 7); c.fill(); } });
      const BR = 0.35;
      const ballM = mesh(new THREE.SphereGeometry(BR, 18, 14), new THREE.MeshLambertMaterial({ map: ballTex }), 0, BR, 0); sc.add(ballM);
      const ball = { p: V3(0, BR, 0), v: V3(0, 0, 0) };
      // вратарь
      const km = makeKid({ skin: pick(KID_SKINS), shirt: 0xfdd835, pants: 0x111111, hair: 0x111111, hairStyle: 'buzz', height: 1.05 });
      for (const a of km.userData.arms) { const gl = mesh(G_BOX, mat(0x43a047), 0, -0.55, 0); gl.scale.set(0.2, 0.2, 0.2); a.add(gl); }
      sc.add(km);
      const keeper = ent(km, 0, -HZ + 0.9); keeper.yaw = 0;
      const ksp = [1.8, 2.4, 3.0][d];
      const defs = [];
      for (let i = 0; i < [0, 1, 2][d]; i++) {
        const m = makeKid({ skin: pick(KID_SKINS), shirt: 0x1e88e5, pants: 0xffffff, hair: pick(HAIR_COLS), hairStyle: pick(STYLES), height: 1.0 });
        sc.add(m);
        const e = ent(m, i ? 4 : -4, -10); e.home = { x: i ? 4 : -4, z: -11 }; e.cd = 0; defs.push(e);
      }
      const dsp = [0, 3.3, 3.9][d];
      const need = [2, 3, 4][d];
      let goals = 0, resetT = 0, kickCd = 0, saveCd = 0;
      Lv.spawn = { x: 0, z: 4 };
      const resetBall = () => { ball.p.set(0, BR, 0); ball.v.set(0, 0, 0); P.pos.set(0, 0, 3); P.vel.set(0, 0, 0); keeper.pos.x = 0; defs.forEach(e => e.pos.set(e.home.x, 0, e.home.z)); };
      Lv.goal = () => `⚽ Голы ${goals}/${need}`;
      Lv.pointer = () => resetT > 0 ? null : (dist2D(ball.p, P.pos) > 2.5 ? ball.p : { x: 0, z: -HZ });
      Lv.onAction = () => {
        if (kickCd > 0 || resetT > 0) return;
        const dd = dist2D(ball.p, P.pos);
        if (dd > 1.3 * st.reach + 0.5) { toast('Подбеги к мячу ⚽'); return; }
        kickCd = 0.4;
        let fx = Math.sin(P.yaw), fz = Math.cos(P.yaw);
        const bx = (ball.p.x - P.pos.x) / (dd || 1), bz = (ball.p.z - P.pos.z) / (dd || 1);
        fx = fx * 0.75 + bx * 0.25; fz = fz * 0.75 + bz * 0.25;
        const fl = Math.hypot(fx, fz) || 1;
        const pw = 13 * Math.sqrt(st.power) + 3;
        ball.v.set(fx / fl * pw, 3.2, fz / fl * pw);
        SFX.punch(); beep(320, 0.08, 'triangle', 0.1);
      };
      Lv.update = (dt) => {
        kickCd -= dt; saveCd -= dt;
        sc.children.forEach(o => { if (o.userData.fan) o.position.y += Math.sin(G.time * 8 + o.position.z) * dt * (goals ? 1.2 : 0.3); });
        if (resetT > 0) { resetT -= dt; if (resetT <= 0) resetBall(); }
        // физика мяча
        ball.v.y -= 20 * dt;
        ball.p.addScaledVector(ball.v, dt);
        if (ball.p.y < BR) { ball.p.y = BR; ball.v.y = Math.abs(ball.v.y) > 2 ? -ball.v.y * 0.45 : 0; }
        const fr = ball.p.y <= BR + 0.01 ? Math.exp(-1.1 * dt) : Math.exp(-0.15 * dt);
        ball.v.x *= fr; ball.v.z *= fr;
        if (ball.p.x > HX - BR) { ball.p.x = HX - BR; ball.v.x *= -0.7; }
        if (ball.p.x < -HX + BR) { ball.p.x = -HX + BR; ball.v.x *= -0.7; }
        if (ball.p.z > HZ - BR) { ball.p.z = HZ - BR; ball.v.z *= -0.7; }
        const inMouth = Math.abs(ball.p.x) < GW - 0.15 && ball.p.y < 2.3;
        if (ball.p.z < -HZ + BR && !inMouth && ball.p.z > -HZ - 0.3) { ball.p.z = -HZ + BR; ball.v.z *= -0.7; }
        if (ball.p.z < -HZ - 1.8) { ball.p.z = -HZ - 1.8; ball.v.z *= -0.2; }
        if (ball.p.z < -HZ - 0.2 && Math.abs(ball.p.x) > GW - 0.2) { ball.p.x = Math.sign(ball.p.x) * (GW - 0.2); ball.v.x *= -0.5; }
        if (ball.p.y > 2.3 && ball.p.z < -HZ + 0.3 && ball.p.z > -HZ - 0.3 && Math.abs(ball.p.x) < GW) { ball.v.z = Math.abs(ball.v.z) * 0.6; ball.p.z = -HZ + 0.35; }
        // гол
        if (resetT <= 0 && ball.p.z < -HZ - 0.4 && Math.abs(ball.p.x) < GW) {
          goals++; resetT = 1.8;
          bigMsg('ГОООЛ! ⚽', '#ffe14d', 1500); SFX.win(); burst(ball.p, KID_COLORS, 30, 8);
          if (goals >= need) later(win, 600);
        }
        // ведение
        const dx = ball.p.x - P.pos.x, dz = ball.p.z - P.pos.z, dd = Math.hypot(dx, dz);
        if (dd < P.r + BR + 0.15 && ball.p.y < 1.2 && resetT <= 0) {
          const nx = dx / (dd || 1), nz = dz / (dd || 1);
          ball.p.x = P.pos.x + nx * (P.r + BR + 0.16); ball.p.z = P.pos.z + nz * (P.r + BR + 0.16);
          const pv = P.vel.x * nx + P.vel.z * nz;
          ball.v.x = P.vel.x * 1.1 + nx * Math.max(1.5, pv * 0.3); ball.v.z = P.vel.z * 1.1 + nz * Math.max(1.5, pv * 0.3);
        }
        // вратарь
        const aimX = clamp(ball.p.z < -6 ? ball.p.x + ball.v.x * 0.15 : ball.p.x * 0.35, -GW + 0.6, GW - 0.6);
        const kd = aimX - keeper.pos.x;
        keeper.pos.x += clamp(kd, -ksp * dt, ksp * dt);
        keeper.pos.z = -HZ + 0.9;
        keeper.mesh.position.copy(keeper.pos); keeper.mesh.rotation.y = 0;
        animKid(km, dt, Math.min(1, Math.abs(kd) * 2), false);
        if (Math.abs(kd) < 0.3) { km.userData.arms[0].rotation.z = -0.8; km.userData.arms[1].rotation.z = 0.8; }
        if (saveCd <= 0 && resetT <= 0 && Math.abs(ball.p.x - keeper.pos.x) < 0.75 + d * 0.1 && Math.abs(ball.p.z - keeper.pos.z) < 0.8 && ball.p.y < 2.2) {
          saveCd = 0.6;
          ball.v.set(rand(-6, 6), 3, Math.abs(ball.v.z) * 0.4 + 7); ball.p.z = keeper.pos.z + 0.9;
          toast('Вратарь отбил! 🧤'); SFX.punch();
        }
        // защитники
        for (const e of defs) {
          e.cd -= dt;
          const tg = ball.p.z < 4 && resetT <= 0 ? ball.p : e.home;
          steer(e, tg.x - e.pos.x, tg.z - e.pos.z, dist2D(tg, e.pos) > 0.3 ? dsp : 0, dt, Lv, 6);
          animKid(e.mesh, dt, Math.hypot(e.vel.x, e.vel.z) / 5, false);
          if (e.cd <= 0 && dist2D(e.pos, ball.p) < 0.85 && ball.p.y < 1.2) {
            e.cd = 1.2; ball.v.set(rand(-5, 5), 2, rand(9, 13)); beep(260, 0.08, 'triangle', 0.08);
            toast('Защитник отобрал мяч!');
          }
          const pdx = P.pos.x - e.pos.x, pdz = P.pos.z - e.pos.z, pd = Math.hypot(pdx, pdz);
          if (pd < 0.75 && pd > 0.01) { P.pos.x += pdx / pd * (0.75 - pd); P.pos.z += pdz / pd * (0.75 - pd); }
        }
        ballM.position.copy(ball.p);
        ballM.rotation.x -= ball.v.z * dt / BR; ballM.rotation.z += ball.v.x * dt / BR;
      };
      return Lv;
    }
  }
];
