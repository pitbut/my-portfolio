import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const SHOP_ID = window.SHOP_ID;
const wrap = document.getElementById('canvas-wrap');
const socket = io();
socket.emit('join_shop', { shop_id: SHOP_ID });

// ---------- сцена / камера / рендер ----------
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x05060a);
scene.fog = new THREE.Fog(0x05060a, 6, 18);

const camera = new THREE.PerspectiveCamera(50, window.innerWidth / window.innerHeight, 0.1, 100);
camera.position.set(0, 1.8, 5.5);

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
wrap.appendChild(renderer.domElement);

const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(0, 1, 0);
controls.enableDamping = true;
controls.minDistance = 2;
controls.maxDistance = 9;
controls.maxPolarAngle = Math.PI * 0.49;

window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});

// ---------- свет ----------
scene.add(new THREE.AmbientLight(0x8899aa, 0.6));
const key = new THREE.DirectionalLight(0xffffff, 1.1);
key.position.set(3, 6, 4);
scene.add(key);
const accent = new THREE.PointLight(0x5eead4, 1.2, 10);
accent.position.set(0, 2.5, -1);
scene.add(accent);

// ---------- пол + стена + витрина (простая геометрия, цвета из оформления магазина) ----------
const theme = window.SHOP_THEME || {};
const floorColorHex = theme.floorColor || '#11141c';
const wallColorHex = theme.wallColor || '#141821';

const floor = new THREE.Mesh(
  new THREE.PlaneGeometry(20, 20),
  new THREE.MeshStandardMaterial({ color: new THREE.Color(floorColorHex), roughness: 0.9 })
);
floor.rotation.x = -Math.PI / 2;
scene.add(floor);

// задняя стена
const wall = new THREE.Mesh(
  new THREE.PlaneGeometry(12, 5),
  new THREE.MeshStandardMaterial({ color: new THREE.Color(wallColorHex), roughness: 0.95 })
);
wall.position.set(0, 2.5, -2.5);
scene.add(wall);

if (theme.hasWindow) {
  const windowPane = new THREE.Mesh(
    new THREE.PlaneGeometry(2, 2.4),
    new THREE.MeshStandardMaterial({ color: 0x9fd8e8, emissive: 0x3a5a66, emissiveIntensity: 0.4 })
  );
  windowPane.position.set(-3.5, 2.6, -2.48);
  scene.add(windowPane);
}

if (theme.hasPainting) {
  const frame = new THREE.Mesh(
    new THREE.PlaneGeometry(1.3, 1.0),
    new THREE.MeshStandardMaterial({ color: 0xf0a860 })
  );
  frame.position.set(3.3, 2.7, -2.48);
  scene.add(frame);
}

if (theme.hasPlant) {
  const pot = new THREE.Mesh(
    new THREE.CylinderGeometry(0.22, 0.18, 0.3, 16),
    new THREE.MeshStandardMaterial({ color: 0x5a4632 })
  );
  pot.position.set(-3.6, 0.15, 1.2);
  scene.add(pot);
  const leaves = new THREE.Mesh(
    new THREE.ConeGeometry(0.4, 0.9, 8),
    new THREE.MeshStandardMaterial({ color: 0x4a8a5a })
  );
  leaves.position.set(-3.6, 0.75, 1.2);
  scene.add(leaves);
}

const shelf = new THREE.Mesh(
  new THREE.BoxGeometry(4.2, 0.08, 0.6),
  new THREE.MeshStandardMaterial({ color: 0x1b2130, roughness: 0.6, metalness: 0.2 })
);
shelf.position.set(0, 1.0, -1.5);
scene.add(shelf);

// стол продавца
const table = new THREE.Mesh(
  new THREE.CylinderGeometry(0.5, 0.5, 0.06, 32),
  new THREE.MeshStandardMaterial({ color: 0x2a3244, roughness: 0.5, metalness: 0.3 })
);
table.position.set(0, 0.75, 1.6);
scene.add(table);
const tableLeg = new THREE.Mesh(
  new THREE.CylinderGeometry(0.08, 0.08, 0.75, 16),
  new THREE.MeshStandardMaterial({ color: 0x1b2130 })
);
tableLeg.position.set(0, 0.375, 1.6);
scene.add(tableLeg);

// ---------- ценник (canvas -> спрайт) ----------
function makePriceTag(text) {
  const canvas = document.createElement('canvas');
  canvas.width = 256; canvas.height = 96;
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = 'rgba(20,24,33,0.9)';
  ctx.beginPath();
  ctx.roundRect(4, 4, 248, 88, 12);
  ctx.fill();
  ctx.strokeStyle = '#5eead4';
  ctx.lineWidth = 2;
  ctx.stroke();
  ctx.fillStyle = '#f0a860';
  ctx.font = 'bold 40px Space Grotesk, sans-serif';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(text, 128, 52);
  const tex = new THREE.CanvasTexture(canvas);
  const mat = new THREE.SpriteMaterial({ map: tex, transparent: true });
  const sprite = new THREE.Sprite(mat);
  sprite.scale.set(0.9, 0.34, 1);
  return sprite;
}

function fmtPrice(p) {
  return Math.round(p).toLocaleString('ru-RU') + ' сум';
}

// ---------- загрузка товаров магазина ----------
const loader = new GLTFLoader();
const productObjects = {}; // id -> { root, shelfPos, onTable, spinning }
let activeProduct = null;

async function loadShop() {
  const res = await fetch(`/api/shops/${SHOP_ID}/products`);
  const products = await res.json();
  products.forEach((p) => loadProduct(p));
}

function loadProduct(p) {
  loader.load(p.model_url, (gltf) => {
    const root = gltf.scene;
    root.traverse((o) => { if (o.isMesh) { o.castShadow = true; } });

    const shelfPos = new THREE.Vector3(p.shelf_x, 1.22, -1.5);
    root.position.copy(shelfPos);
    root.userData.productId = p.id;
    scene.add(root);

    const tag = makePriceTag(fmtPrice(p.price));
    tag.position.copy(shelfPos).add(new THREE.Vector3(0, 0.35, 0));
    scene.add(tag);

    productObjects[p.id] = { root, tag, shelfPos, onTable: false, data: p };
  }, undefined, (err) => console.error('model load error', p.model_url, err));
}

loadShop();

// ---------- клик по товару ----------
const raycaster = new THREE.Raycaster();
const mouse = new THREE.Vector2();

renderer.domElement.addEventListener('click', (event) => {
  mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
  mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;
  raycaster.setFromCamera(mouse, camera);

  const roots = Object.values(productObjects).map((o) => o.root);
  const intersects = raycaster.intersectObjects(roots, true);
  if (intersects.length === 0) return;

  let obj = intersects[0].object;
  while (obj && !obj.userData.productId) obj = obj.parent;
  if (!obj) return;
  selectProduct(obj.userData.productId);
});

function selectProduct(id, opts = {}) {
  // вернуть предыдущий товар на полку
  if (activeProduct !== null && activeProduct !== id) {
    returnToShelf(activeProduct);
  }
  activeProduct = id;
  const entry = productObjects[id];
  entry.onTable = true;

  animateTo(entry.root, new THREE.Vector3(0, 1.05, 1.6), 0.6);
  entry.tag.visible = false;

  openSellerPanel(entry.data);

  if (!opts.remote) {
    socket.emit('select_product', { shop_id: SHOP_ID, product_id: id });
  }
}

// когда кто-то другой в этом же магазине (друг по приглашению) выбирает товар -
// показываем то же самое у нас, без повторной отправки события
socket.on('product_selected', ({ product_id }) => {
  if (productObjects[product_id]) {
    selectProduct(product_id, { remote: true });
  }
});

function returnToShelf(id) {
  const entry = productObjects[id];
  if (!entry) return;
  entry.onTable = false;
  animateTo(entry.root, entry.shelfPos, 0.6);
  entry.tag.visible = true;
}

function animateTo(obj, targetPos, duration) {
  const start = obj.position.clone();
  const startTime = performance.now();
  function step(now) {
    const t = Math.min(1, (now - startTime) / (duration * 1000));
    const ease = t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
    obj.position.lerpVectors(start, targetPos, ease);
    if (t < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

// ---------- анимация: вращение товара на столе ----------
function animate() {
  requestAnimationFrame(animate);
  for (const id in productObjects) {
    const entry = productObjects[id];
    if (entry.onTable) {
      entry.root.rotation.y += 0.012;
    }
  }
  controls.update();
  renderer.render(scene, camera);
}
animate();

// ============================================================
// UI: панель продавца, отзывы, покупка, приглашение
// ============================================================

const panel = document.getElementById('seller-panel');
const sellerText = document.getElementById('seller-text');
const sellerPrice = document.getElementById('seller-price');
const reviewsBtn = document.getElementById('reviews-btn');
const buyBtn = document.getElementById('buy-btn');
const reviewsBox = document.getElementById('reviews-box');
const buyBox = document.getElementById('buy-box');

let currentProductData = null;

function openSellerPanel(p) {
  currentProductData = p;
  panel.classList.remove('hidden');
  reviewsBox.classList.add('hidden');
  buyBox.classList.add('hidden');
  sellerText.textContent = p.description || `${p.name} — отличный выбор.`;
  sellerPrice.textContent = fmtPrice(p.price);

  // виртуальный продавец "говорит" (браузерный TTS, если доступен)
  try {
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
      const utter = new SpeechSynthesisUtterance(sellerText.textContent);
      utter.lang = 'ru-RU';
      window.speechSynthesis.speak(utter);
    }
  } catch (e) { /* тихо игнорируем, если TTS недоступен */ }
}

document.getElementById('seller-close').addEventListener('click', () => {
  panel.classList.add('hidden');
  if (activeProduct !== null) returnToShelf(activeProduct);
  activeProduct = null;
  try { window.speechSynthesis && window.speechSynthesis.cancel(); } catch (e) {}
});

reviewsBtn.addEventListener('click', async () => {
  reviewsBox.classList.toggle('hidden');
  buyBox.classList.add('hidden');
  if (reviewsBox.classList.contains('hidden') || !currentProductData) return;
  const res = await fetch(`/api/reviews/product/${currentProductData.id}`);
  const reviews = await res.json();
  const shopRes = await fetch(`/api/reviews/shop/${currentProductData.shop_id}`);
  const shopReviews = await shopRes.json();
  reviewsBox.innerHTML =
    `<b>О товаре:</b>` +
    (reviews.length ? reviews.map((r) => `<div class="review-line">★${r.rating} ${r.author}: ${r.text}</div>`).join('')
      : `<div class="review-line">Пока нет отзывов о товаре.</div>`) +
    `<b>О магазине:</b>` +
    (shopReviews.length ? shopReviews.map((r) => `<div class="review-line">★${r.rating} ${r.author}: ${r.text}</div>`).join('')
      : `<div class="review-line">Пока нет отзывов о магазине.</div>`);
});

buyBtn.addEventListener('click', () => {
  buyBox.classList.toggle('hidden');
  reviewsBox.classList.add('hidden');
  if (buyBox.classList.contains('hidden')) return;
  buyBox.innerHTML = `
    <label>Адрес доставки</label>
    <input id="addr-input" placeholder="Город, улица, дом">
    <button id="geo-btn" class="btn-secondary" style="margin-bottom:8px;">Определить геолокацию</button>
    <div id="geo-result" style="font-size:12px;color:#8b93a7;margin-bottom:8px;"></div>
    <button id="confirm-buy" class="btn-primary">Оформить заказ</button>
    <div id="order-result" style="margin-top:10px;"></div>
  `;
  let coords = null;
  document.getElementById('geo-btn').addEventListener('click', () => {
    if (!navigator.geolocation) { document.getElementById('geo-result').textContent = 'Геолокация недоступна в браузере.'; return; }
    navigator.geolocation.getCurrentPosition((pos) => {
      coords = { lat: pos.coords.latitude, lng: pos.coords.longitude };
      document.getElementById('geo-result').textContent = `Координаты: ${coords.lat.toFixed(4)}, ${coords.lng.toFixed(4)}`;
    }, () => { document.getElementById('geo-result').textContent = 'Не удалось получить геолокацию.'; });
  });
  document.getElementById('confirm-buy').addEventListener('click', async () => {
    const address = document.getElementById('addr-input').value;
    const res = await fetch('/api/orders', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ product_id: currentProductData.id, address, lat: coords?.lat, lng: coords?.lng }),
    });
    const data = await res.json();
    document.getElementById('order-result').innerHTML =
      `Заказ #${data.order_id} создан. Переведите оплату на карту:<br>` +
      `<span class="card-number">${data.card_number}</span><br>` +
      `Статус: ${data.status}`;
  });
});

// ---------- приглашение друзей ----------
document.getElementById('invite-btn').addEventListener('click', async () => {
  const box = document.getElementById('invite-box');
  const res = await fetch(`/api/shops/${SHOP_ID}/invite`, { method: 'POST' });
  const data = await res.json();
  const fullUrl = `${window.location.origin}${data.url}`;
  box.classList.remove('hidden');
  box.innerHTML = `Ссылка для друзей (открывают тот же магазин):<br><a href="${fullUrl}" style="color:#5eead4">${fullUrl}</a>`;
});

// ============================================================
// Голосовой чат через PeerJS (тот же подход, что уже работал в VR-кафе:
// PeerJS сам берёт на себя WebRTC-хендшейк и STUN/TURN через свой бесплатный
// облачный брокер - наш сервер только передаёт PeerJS-идентификаторы между
// участниками комнаты).
// ============================================================

let peer = null;
let peerReady = null; // Promise, резолвится, когда получили свой PeerJS ID
let localStream = null;
let currentVoiceChannel = null; // null | 'all' | 'friends'
const mediaCalls = {}; // peerId -> PeerJS MediaConnection

function setVoiceStatus(text) {
  const el = document.getElementById('voice-status');
  if (!text) { el.classList.add('hidden'); el.textContent = ''; return; }
  el.classList.remove('hidden');
  el.textContent = text;
}

function updateVoiceButtons() {
  document.getElementById('voice-all-btn').classList.toggle('active', currentVoiceChannel === 'all');
  document.getElementById('voice-friends-btn').classList.toggle('active', currentVoiceChannel === 'friends');
}

function ensurePeer() {
  if (peerReady) return peerReady;
  peer = new Peer(); // подключается к бесплатному облачному брокеру PeerJS
  peerReady = new Promise((resolve) => {
    peer.on('open', (id) => resolve(id));
  });
  peer.on('call', (call) => {
    // кто-то уже в комнате звонит нам - отвечаем своим потоком
    if (!localStream) return;
    call.answer(localStream);
    attachRemoteAudio(call);
  });
  peer.on('error', (err) => {
    console.error('PeerJS error', err);
    setVoiceStatus('Ошибка голосового соединения');
  });
  return peerReady;
}

function attachRemoteAudio(call) {
  mediaCalls[call.peer] = call;
  call.on('stream', (remoteStream) => {
    let audioEl = document.getElementById(`voice-audio-${call.peer}`);
    if (!audioEl) {
      audioEl = document.createElement('audio');
      audioEl.id = `voice-audio-${call.peer}`;
      audioEl.autoplay = true;
      document.body.appendChild(audioEl);
    }
    audioEl.srcObject = remoteStream;
  });
  call.on('close', () => closeCall(call.peer));
}

function closeCall(peerId) {
  const call = mediaCalls[peerId];
  if (call) { call.close(); delete mediaCalls[peerId]; }
  const audioEl = document.getElementById(`voice-audio-${peerId}`);
  if (audioEl) audioEl.remove();
}

async function toggleVoice(channel) {
  if (currentVoiceChannel === channel) { leaveVoice(); return; }
  if (currentVoiceChannel) leaveVoiceInternal(currentVoiceChannel);

  if (!localStream) {
    try {
      localStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (e) {
      setVoiceStatus('Нет доступа к микрофону — разрешите доступ в браузере');
      return;
    }
  }
  const myPeerId = await ensurePeer();
  currentVoiceChannel = channel;
  updateVoiceButtons();
  setVoiceStatus(channel === 'all' ? '🎤 Голосовой чат: все' : '🎤 Голосовой чат: только друзья (без продавца)');
  socket.emit('join_voice', { shop_id: SHOP_ID, channel, peer_id: myPeerId });
}

function leaveVoice() {
  if (!currentVoiceChannel) return;
  leaveVoiceInternal(currentVoiceChannel);
  currentVoiceChannel = null;
  updateVoiceButtons();
  setVoiceStatus(null);
}

function leaveVoiceInternal(channel) {
  socket.emit('leave_voice', { shop_id: SHOP_ID, channel });
  Object.keys(mediaCalls).forEach((peerId) => closeCall(peerId));
}

// сервер сообщает, кто уже в комнате - звоним им сами через PeerJS
socket.on('voice_existing_peers', ({ peer_ids }) => {
  if (!currentVoiceChannel || !localStream) return;
  peer_ids.forEach((peerId) => {
    const call = peer.call(peerId, localStream);
    attachRemoteAudio(call);
  });
});

socket.on('voice_peer_left', ({ peer_id }) => closeCall(peer_id));

socket.on('voice_error', ({ message }) => {
  setVoiceStatus(message);
  setTimeout(() => { if (!currentVoiceChannel) setVoiceStatus(null); }, 3000);
});

document.getElementById('voice-all-btn').addEventListener('click', () => toggleVoice('all'));
document.getElementById('voice-friends-btn').addEventListener('click', () => toggleVoice('friends'));
