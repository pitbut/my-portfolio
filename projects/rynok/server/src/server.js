'use strict';

/**
 * Сервер-релей приложения «Рынок».
 *
 * Задача сервера — только связать два телефона одной семьи и передать
 * между ними сообщения в реальном времени (список покупок, отметки о
 * покупке, чат). Долговременного хранилища истории здесь нет: каждое
 * сообщение хранится в памяти лишь до того, как второй участник семьи
 * его получит (или недолго, если он сейчас офлайн), после чего
 * забывается сервером. Вся история остаётся только локально на
 * телефонах (в Room-базе приложения) — если пользователь чистит кэш
 * приложения, история пропадает только у него, это ожидаемое поведение.
 */

const express = require('express');
const http = require('http');
const crypto = require('crypto');
const multer = require('multer');
const { WebSocketServer } = require('ws');

const PORT = process.env.PORT || 3000;

// Сколько живёт код приглашения, если им никто не воспользовался.
const CODE_TTL_MS = 24 * 60 * 60 * 1000; // 24 часа
// Сколько сервер хранит недоставленное сообщение в буфере для офлайн-получателя.
const MESSAGE_BUFFER_TTL_MS = 12 * 60 * 60 * 1000; // 12 часов
// Сколько живёт временный медиафайл (голосовое/видео сообщение) на сервере.
const MEDIA_TTL_MS = 12 * 60 * 60 * 1000; // 12 часов
const MAX_MEDIA_BYTES = 25 * 1024 * 1024; // 25 МБ на файл

/** familyId -> { code, createdAt, members: Map<role, Set<ws>>, buffer: Array<{event, expiresAt}> } */
const families = new Map();
/** code -> familyId */
const codesByValue = new Map();
/** mediaId -> { buffer, mime, expiresAt } */
const mediaStore = new Map();

function generateFamilyCode() {
  // 6-значный числовой код, который легко продиктовать по телефону.
  let code;
  do {
    code = String(crypto.randomInt(100000, 1000000));
  } while (codesByValue.has(code));
  return code;
}

function createFamily() {
  const familyId = crypto.randomUUID();
  const code = generateFamilyCode();
  families.set(familyId, {
    code,
    createdAt: Date.now(),
    members: new Map(), // role ('wife' | 'husband') -> Set<ws>
    buffer: [],
  });
  codesByValue.set(code, familyId);
  return { familyId, code };
}

function sweepExpired() {
  const now = Date.now();

  for (const [familyId, family] of families) {
    family.buffer = family.buffer.filter((entry) => entry.expiresAt > now);
    // Семью без единого подключения и без свежего кода можно убрать через сутки.
    if (now - family.createdAt > CODE_TTL_MS && family.members.size === 0) {
      families.delete(familyId);
      codesByValue.delete(family.code);
    }
  }

  for (const [mediaId, media] of mediaStore) {
    if (media.expiresAt <= now) {
      mediaStore.delete(mediaId);
    }
  }
}
setInterval(sweepExpired, 10 * 60 * 1000).unref();

const app = express();
app.use(express.json({ limit: '1mb' }));

const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: MAX_MEDIA_BYTES },
});

app.get('/health', (_req, res) => {
  res.json({ ok: true, families: families.size });
});

// Жена (или тот, кто первый открыл приложение) создаёт семью и получает код.
app.post('/api/family', (_req, res) => {
  const { familyId, code } = createFamily();
  res.json({ familyId, code, expiresInMs: CODE_TTL_MS });
});

// Второй участник вводит код, полученный от первого, и присоединяется.
app.post('/api/family/join', (req, res) => {
  const code = String(req.body?.code || '').trim();
  const familyId = codesByValue.get(code);
  if (!familyId || !families.has(familyId)) {
    return res.status(404).json({ error: 'invite_code_not_found' });
  }
  res.json({ familyId });
});

// Загрузка голосового/видео сообщения для чата. Файл живёт недолго —
// ровно столько, чтобы получатель успел его скачать при следующем подключении.
app.post('/api/media', upload.single('file'), (req, res) => {
  if (!req.file) {
    return res.status(400).json({ error: 'file_required' });
  }
  const mediaId = crypto.randomUUID();
  mediaStore.set(mediaId, {
    buffer: req.file.buffer,
    mime: req.file.mimetype || 'application/octet-stream',
    expiresAt: Date.now() + MEDIA_TTL_MS,
  });
  res.json({ mediaId, expiresInMs: MEDIA_TTL_MS });
});

app.get('/api/media/:mediaId', (req, res) => {
  const media = mediaStore.get(req.params.mediaId);
  if (!media || media.expiresAt <= Date.now()) {
    return res.status(404).end();
  }
  res.setHeader('Content-Type', media.mime);
  res.setHeader('Cache-Control', 'private, max-age=0, no-store');
  res.send(media.buffer);
});

const server = http.createServer(app);
const wss = new WebSocketServer({ server, path: '/ws' });

function otherRole(role) {
  return role === 'wife' ? 'husband' : 'wife';
}

function send(ws, event) {
  if (ws.readyState === ws.OPEN) {
    ws.send(JSON.stringify(event));
  }
}

wss.on('connection', (ws, req) => {
  const url = new URL(req.url, 'http://localhost');
  const familyId = url.searchParams.get('familyId');
  const role = url.searchParams.get('role'); // 'wife' | 'husband'

  const family = familyId ? families.get(familyId) : null;
  if (!family || (role !== 'wife' && role !== 'husband')) {
    ws.close(4400, 'invalid_family_or_role');
    return;
  }

  if (!family.members.has(role)) {
    family.members.set(role, new Set());
  }
  family.members.get(role).add(ws);

  // При подключении отдаём всё, что накопилось в буфере, пока устройство было офлайн.
  const now = Date.now();
  const pending = family.buffer.filter((e) => e.expiresAt > now && e.forRole === role);
  for (const entry of pending) {
    send(ws, entry.event);
  }
  family.buffer = family.buffer.filter((e) => !(e.expiresAt > now && e.forRole === role));

  send(ws, { type: 'connected', role, familyId });

  ws.on('message', (raw) => {
    let event;
    try {
      event = JSON.parse(raw.toString());
    } catch {
      return;
    }
    if (!event || typeof event.type !== 'string') return;

    // Разрешённые типы событий: list:update, item:update, chat:message, budget:summary, typing
    const targetRole = otherRole(role);
    const targets = family.members.get(targetRole);
    const delivered = targets && targets.size > 0;

    if (delivered) {
      for (const targetWs of targets) {
        send(targetWs, { ...event, fromRole: role });
      }
    } else {
      // Получатель офлайн — кладём в буфер, доставим при подключении.
      family.buffer.push({
        forRole: targetRole,
        expiresAt: Date.now() + MESSAGE_BUFFER_TTL_MS,
        event: { ...event, fromRole: role },
      });
    }
  });

  ws.on('close', () => {
    family.members.get(role)?.delete(ws);
  });
});

server.listen(PORT, () => {
  console.log(`rynok relay server listening on :${PORT}`);
});
