'use strict';
/* ===== 3D-модели: дети, зомби, члены экипажа, предметы ===== */

const MAT_CACHE = {};
function mat(color, opts) {
  const key = color + (opts ? JSON.stringify(opts) : '');
  if (!MAT_CACHE[key]) MAT_CACHE[key] = new THREE.MeshLambertMaterial(Object.assign({ color }, opts || {}));
  return MAT_CACHE[key];
}
function clearMatCache() {
  for (const k in MAT_CACHE) { MAT_CACHE[k].dispose(); delete MAT_CACHE[k]; }
}

function mesh(geo, material, x, y, z, cast) {
  const m = new THREE.Mesh(geo, material);
  m.position.set(x || 0, y || 0, z || 0);
  if (cast !== false) m.castShadow = true;
  m.receiveShadow = true;
  return m;
}

// Текстура из canvas
function canvasTex(size, draw, rx, ry) {
  const cv = document.createElement('canvas');
  cv.width = cv.height = size;
  const ctx = cv.getContext('2d');
  draw(ctx, size);
  const t = new THREE.CanvasTexture(cv);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.repeat.set(rx || 1, ry || rx || 1);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 4;
  return t;
}

function noiseTex(base, spots, rx, alpha) {
  return canvasTex(128, (c, s) => {
    c.fillStyle = base; c.fillRect(0, 0, s, s);
    for (let i = 0; i < 500; i++) {
      c.fillStyle = spots[i % spots.length];
      c.globalAlpha = alpha || 0.35;
      const r = 1 + Math.random() * 3;
      c.fillRect(Math.random() * s, Math.random() * s, r, r);
    }
    c.globalAlpha = 1;
  }, rx);
}

// Табличка с текстом (спрайт)
function textSprite(text, color, bg, scale) {
  const cv = document.createElement('canvas');
  cv.width = 256; cv.height = 64;
  const c = cv.getContext('2d');
  c.font = 'bold 38px Arial, sans-serif';
  c.textAlign = 'center'; c.textBaseline = 'middle';
  if (bg) {
    const w = Math.min(250, c.measureText(text).width + 30);
    c.fillStyle = bg;
    roundRect(c, 128 - w / 2, 6, w, 52, 18); c.fill();
  }
  c.lineWidth = 6; c.strokeStyle = 'rgba(0,0,0,0.55)';
  c.strokeText(text, 128, 34);
  c.fillStyle = color || '#fff';
  c.fillText(text, 128, 34);
  const t = new THREE.CanvasTexture(cv);
  t.colorSpace = THREE.SRGBColorSpace;
  const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: t, depthTest: false, transparent: true }));
  const sc = scale || 1.6;
  sp.scale.set(sc, sc / 4, 1);
  sp.renderOrder = 10;
  return sp;
}
function roundRect(c, x, y, w, h, r) {
  c.beginPath();
  c.moveTo(x + r, y); c.arcTo(x + w, y, x + w, y + h, r); c.arcTo(x + w, y + h, x, y + h, r);
  c.arcTo(x, y + h, x, y, r); c.arcTo(x, y, x + w, y, r); c.closePath();
}

const G_BOX = new THREE.BoxGeometry(1, 1, 1);
const G_SPH = new THREE.SphereGeometry(1, 16, 12);
const G_CYL = new THREE.CylinderGeometry(1, 1, 1, 16);

/*
  Ребёнок из простых фигур. Параметры:
  height (рост, множитель ног/туловища), skin, shirt, pants, hair, hairStyle,
  glasses, hat ('cap' | 'crown' | null), costume ('spider' | 'zombie' | 'squid')
*/
function makeKid(o) {
  const H = o.height || 1;
  const g = new THREE.Group();
  const body = new THREE.Group();
  g.add(body);
  const skin = mat(o.skin || 0xf0c09a);
  const shirt = mat(o.shirt || 0x3366ff);
  const pants = mat(o.pants || 0x223344);
  const shoes = mat(o.shoes || 0x222222);
  const hairM = mat(o.hair || 0x2a1a0e);

  const hip = 0.72 * H, torsoH = 0.56 * H, shoulder = hip + torsoH - 0.06;
  // ноги
  const legs = [];
  for (const sx of [-0.13, 0.13]) {
    const p = new THREE.Group(); p.position.set(sx, hip, 0);
    const leg = mesh(G_BOX, pants, 0, -hip / 2 + 0.06, 0); leg.scale.set(0.2, hip - 0.1, 0.22);
    const shoe = mesh(G_BOX, shoes, 0, -hip + 0.06, 0.05); shoe.scale.set(0.22, 0.12, 0.32);
    p.add(leg, shoe); body.add(p); legs.push(p);
  }
  // туловище
  const torso = mesh(G_BOX, shirt, 0, hip + torsoH / 2, 0); torso.scale.set(0.56, torsoH, 0.32);
  body.add(torso);
  // руки
  const arms = [];
  for (const sx of [-0.36, 0.36]) {
    const p = new THREE.Group(); p.position.set(sx, shoulder, 0);
    const sleeve = mesh(G_BOX, shirt, 0, -0.12, 0); sleeve.scale.set(0.17, 0.26, 0.19);
    const arm = mesh(G_BOX, skin, 0, -0.27 * H - 0.08, 0); arm.scale.set(0.14, 0.3 * H, 0.15);
    p.add(sleeve, arm); body.add(p); arms.push(p);
  }
  // голова
  const headG = new THREE.Group(); headG.position.set(0, hip + torsoH + 0.27, 0);
  body.add(headG);
  const head = mesh(G_SPH, skin, 0, 0, 0); head.scale.set(0.27, 0.29, 0.27);
  headG.add(head);
  const neck = mesh(G_CYL, skin, 0, hip + torsoH + 0.02, 0); neck.scale.set(0.09, 0.1, 0.09); body.add(neck);
  const eyeM = mat(o.eyes || 0x111111);
  for (const sx of [-0.09, 0.09]) {
    const eW = mesh(G_SPH, mat(0xffffff), sx, 0.03, 0.235, false); eW.scale.set(0.055, 0.06, 0.03); headG.add(eW);
    const e = mesh(G_SPH, eyeM, sx, 0.03, 0.258, false); e.scale.set(0.03, 0.035, 0.02); headG.add(e);
  }
  const mouth = mesh(G_BOX, mat(0x8a3b2e), 0, -0.11, 0.25, false); mouth.scale.set(0.1, 0.025, 0.02); headG.add(mouth);

  if (o.costume === 'spider') {
    head.material = mat(0xd61f26);
    headG.children.forEach(ch => { if (ch !== head) ch.visible = false; });
    for (const sx of [-0.1, 0.1]) {
      const e = mesh(G_SPH, mat(0xffffff), sx, 0.04, 0.235, false);
      e.scale.set(0.08, 0.05, 0.03); e.rotation.z = sx > 0 ? -0.5 : 0.5; headG.add(e);
    }
    torso.material = mat(0xd61f26);
    arms.forEach(a => { a.children[0].material = mat(0xd61f26); a.children[1].material = mat(0xd61f26); });
    legs.forEach(l => { l.children[0].material = mat(0x1d4fc4); l.children[1].material = mat(0xd61f26); });
    const logo = mesh(G_SPH, mat(0x111111), 0, hip + torsoH * 0.6, 0.165, false); logo.scale.set(0.06, 0.08, 0.02); body.add(logo);
  } else {
    // причёска
    const style = o.hairStyle || 'short';
    if (style !== 'none') {
      const capH = style === 'buzz' ? 0.45 : 0.55;
      const hairGeo = new THREE.SphereGeometry(1, 16, 10, 0, Math.PI * 2, 0, Math.PI * capH);
      const hr = mesh(hairGeo, hairM, 0, 0.02, -0.01); hr.scale.set(0.29, 0.31, 0.29); headG.add(hr);
      if (style === 'curly') {
        for (let i = 0; i < 9; i++) {
          const a = i / 9 * Math.PI * 2;
          const b = mesh(G_SPH, hairM, Math.cos(a) * 0.2, 0.2, Math.sin(a) * 0.2 - 0.02); b.scale.setScalar(0.1); headG.add(b);
        }
      }
      if (style === 'side') {
        const f = mesh(G_BOX, hairM, 0.06, 0.18, 0.2); f.scale.set(0.3, 0.08, 0.1); f.rotation.z = -0.25; headG.add(f);
      }
      if (style === 'short') {
        const f = mesh(G_BOX, hairM, 0, 0.23, 0.16); f.scale.set(0.38, 0.06, 0.1); headG.add(f);
      }
      if (style === 'pigtails') {
        for (const sx of [-0.3, 0.3]) { const p = mesh(G_SPH, hairM, sx, 0.05, -0.05); p.scale.setScalar(0.12); headG.add(p); }
      }
    }
    if (o.glasses) {
      const gm = mat(0x222222);
      for (const sx of [-0.09, 0.09]) {
        const ring = new THREE.Mesh(new THREE.TorusGeometry(0.065, 0.012, 6, 14), gm);
        ring.position.set(sx, 0.03, 0.27); headG.add(ring);
      }
      const br = mesh(G_BOX, gm, 0, 0.04, 0.275, false); br.scale.set(0.06, 0.015, 0.01); headG.add(br);
    }
  }
  if (o.hat === 'cap') {
    const cm = mat(o.hatColor || 0xff4040);
    const top = mesh(new THREE.SphereGeometry(1, 14, 8, 0, Math.PI * 2, 0, Math.PI / 2), cm, 0, 0.1, 0); top.scale.set(0.3, 0.22, 0.3); headG.add(top);
    const brim = mesh(G_BOX, cm, 0, 0.11, 0.28); brim.scale.set(0.3, 0.03, 0.22); headG.add(brim);
  } else if (o.hat === 'crown') {
    const gm = mat(0xffcc00, { emissive: 0x553300 });
    const ring = mesh(new THREE.CylinderGeometry(0.2, 0.22, 0.14, 12, 1, true), gm, 0, 0.3, 0); headG.add(ring);
    for (let i = 0; i < 6; i++) {
      const a = i / 6 * Math.PI * 2;
      const sp = mesh(new THREE.ConeGeometry(0.05, 0.14, 6), gm, Math.cos(a) * 0.19, 0.42, Math.sin(a) * 0.19); headG.add(sp);
    }
  }

  g.userData = { legs, arms, headG, body, torso, H, t: Math.random() * 10, topY: hip + torsoH + 0.6 };
  return g;
}

// Анимация ходьбы. speed01 — 0..1, air — в прыжке
function animKid(k, dt, speed01, air, mode) {
  const u = k.userData;
  u.t += dt * (4 + speed01 * 9);
  const s = Math.sin(u.t) * 0.8 * speed01;
  if (mode === 'zombie') {
    u.legs[0].rotation.x = s * 0.6; u.legs[1].rotation.x = -s * 0.6;
    u.arms[0].rotation.x = -1.45 + Math.sin(u.t * 0.5) * 0.1;
    u.arms[1].rotation.x = -1.45 - Math.sin(u.t * 0.5) * 0.1;
    u.body.rotation.z = Math.sin(u.t * 0.5) * 0.08;
    return;
  }
  if (mode === 'frozen') {
    u.legs[0].rotation.x = 0.3; u.legs[1].rotation.x = -0.3;
    u.arms[0].rotation.z = -1.2; u.arms[1].rotation.z = 1.2; u.arms[0].rotation.x = 0; u.arms[1].rotation.x = 0;
    return;
  }
  if (mode === 'cheer') {
    u.arms[0].rotation.z = -2.6 + Math.sin(u.t * 2) * 0.3; u.arms[1].rotation.z = 2.6 - Math.sin(u.t * 2) * 0.3;
    u.arms[0].rotation.x = u.arms[1].rotation.x = 0;
    u.body.position.y = Math.abs(Math.sin(u.t * 1.5)) * 0.3;
    return;
  }
  if (mode === 'carry') {
    u.arms[0].rotation.x = u.arms[1].rotation.x = -2.9;
    u.arms[0].rotation.z = u.arms[1].rotation.z = 0;
    u.legs[0].rotation.x = s; u.legs[1].rotation.x = -s;
    u.body.position.y = Math.abs(Math.sin(u.t)) * 0.05 * speed01;
    return;
  }
  u.arms[0].rotation.z = u.arms[1].rotation.z = 0;
  if (air) {
    u.legs[0].rotation.x = 0.6; u.legs[1].rotation.x = -0.3;
    u.arms[0].rotation.x = -2.4; u.arms[1].rotation.x = -2.0;
  } else {
    u.legs[0].rotation.x = s; u.legs[1].rotation.x = -s;
    u.arms[0].rotation.x = -s; u.arms[1].rotation.x = s;
  }
  u.body.position.y = air ? 0 : Math.abs(Math.sin(u.t)) * 0.06 * speed01;
  u.body.rotation.z = 0;
}

const KID_SKINS = [0xf1c8a5, 0xe0ac85, 0xc68e64, 0x9a6a46, 0xf6d6bd];
const KID_COLORS = [0xff595e, 0xffca3a, 0x8ac926, 0x1982c4, 0x6a4c93, 0xff924c, 0x36cfc9, 0xf15bb5];
const HAIR_COLS = [0x1a120b, 0x3b2314, 0x7a4b23, 0xd9a35a, 0x111111];
const STYLES = ['short', 'curly', 'side', 'buzz', 'pigtails'];
function randomKid(extra) {
  return makeKid(Object.assign({
    skin: pick(KID_SKINS), shirt: pick(KID_COLORS), pants: pick([0x223344, 0x444444, 0x2b4a8a, 0x5a3d2b]),
    hair: pick(HAIR_COLS), hairStyle: pick(STYLES), height: 0.9 + Math.random() * 0.15
  }, extra || {}));
}

function makeZombie() {
  const k = makeKid({
    skin: pick([0x7fb069, 0x8fbf6a, 0x6e9e5a]), shirt: pick([0x5b5b5b, 0x6b4b3b, 0x3b4b6b]),
    pants: 0x3a3226, hair: 0x2b2b20, hairStyle: pick(['buzz', 'short', 'none']), eyes: 0xff2020,
    height: 0.95 + Math.random() * 0.15
  });
  return k;
}

// Член экипажа "амогус"
function makeCrewmate(color) {
  const g = new THREE.Group();
  const m = mat(color);
  const body = new THREE.Group(); g.add(body);
  body.add(mesh(new THREE.CapsuleGeometry(0.42, 0.55, 6, 14), m, 0, 0.95, 0));
  const visor = mesh(G_SPH, mat(0x9fdcff, { emissive: 0x224455 }), 0, 1.2, 0.33); visor.scale.set(0.27, 0.16, 0.14); body.add(visor);
  const pack = mesh(G_BOX, m, 0, 0.95, -0.42); pack.scale.set(0.5, 0.6, 0.22); body.add(pack);
  const legs = [];
  for (const sx of [-0.2, 0.2]) {
    const p = new THREE.Group(); p.position.set(sx, 0.45, 0);
    const l = mesh(G_CYL, m, 0, -0.22, 0); l.scale.set(0.15, 0.45, 0.15); p.add(l); g.add(p); legs.push(p);
  }
  g.userData = { legs, arms: [new THREE.Group(), new THREE.Group()], body, headG: new THREE.Group(), t: Math.random() * 9, topY: 1.8 };
  return g;
}

function makeCoin() {
  const g = new THREE.Mesh(new THREE.CylinderGeometry(0.32, 0.32, 0.08, 18), mat(0xffd21f, { emissive: 0x6b4a00 }));
  g.rotation.z = Math.PI / 2;
  g.castShadow = true;
  const w = new THREE.Group(); w.add(g);
  return w;
}

function makeTree(x, z, s) {
  const g = new THREE.Group();
  s = s || 1;
  const tr = mesh(G_CYL, mat(0x7a4b23), 0, 1 * s, 0); tr.scale.set(0.22 * s, 2 * s, 0.22 * s); g.add(tr);
  const col = pick([0x2e8b3d, 0x3aa34a, 0x2f7d32]);
  for (let i = 0; i < 3; i++) {
    const l = mesh(G_SPH, mat(col), (Math.random() - 0.5) * 0.6 * s, (2.3 + i * 0.45) * s, (Math.random() - 0.5) * 0.6 * s);
    l.scale.setScalar((1.1 - i * 0.2) * s); g.add(l);
  }
  g.position.set(x, 0, z);
  return g;
}

function makeBush(x, z, s) {
  const g = new THREE.Group();
  const col = pick([0x3c9a3e, 0x2f8a35, 0x4caf50]);
  for (let i = 0; i < 4; i++) {
    const b = mesh(G_SPH, mat(col), (Math.random() - 0.5) * 1.0 * s, 0.55 * s, (Math.random() - 0.5) * 1.0 * s);
    b.scale.setScalar((0.6 + Math.random() * 0.3) * s); g.add(b);
  }
  g.position.set(x, 0, z);
  return g;
}

function makeCar(color) {
  const g = new THREE.Group();
  const b = mesh(G_BOX, mat(color), 0, 0.6, 0); b.scale.set(1.8, 0.7, 3.8); g.add(b);
  const t = mesh(G_BOX, mat(color), 0, 1.2, -0.2); t.scale.set(1.6, 0.6, 2); g.add(t);
  const w = mesh(G_BOX, mat(0x9fd3ff), 0, 1.2, -0.2, false); w.scale.set(1.62, 0.42, 1.7); g.add(w);
  for (const sx of [-0.9, 0.9]) for (const sz of [-1.2, 1.2]) {
    const wh = mesh(G_CYL, mat(0x111111), sx, 0.35, sz); wh.scale.set(0.35, 0.25, 0.35); wh.rotation.z = Math.PI / 2; g.add(wh);
  }
  return g;
}

function pick(a) { return a[Math.floor(Math.random() * a.length)]; }
function rand(a, b) { return a + Math.random() * (b - a); }
function clamp(v, a, b) { return v < a ? a : v > b ? b : v; }
function shuffle(a) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; }
