# Деплой на VPS — пошагово

Проект живёт внутри монорепозитория `my-portfolio` (`projects/vr-cafe/`) —
так же, как `vr-shop`, `b2b-platform` и другие. При переезде на другой VPS
достаточно одного `git clone` всего `my-portfolio`.

Стек — Node.js (Express + Socket.io + PeerJS), не Flask/Python, как у
остальных проектов на этом VPS — процесс запуска другой (npm вместо venv).

Постройки в кафе хранятся в MongoDB, если задан `MONGODB_URI` — без него
всё работает, но постройки пропадают при каждом рестарте сервиса.
Приглашение в Telegram работает только с `TELEGRAM_BOT_TOKEN` /
`TELEGRAM_CHAT_ID` — без них кнопка приглашения просто не будет ничего
отправлять, остальной сайт не затронут.

## 0. Node.js (если ещё не стоит)

Остальные проекты на этом VPS — на Python, так что Node.js может быть не
установлен. Проверь: `node -v`. Если команда не найдена:

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs
```

## 1. Первый запуск на сервере

```bash
cd /root/my-portfolio   # или куда склонирован монорепозиторий
git pull origin main

cd projects/vr-cafe
npm install --production
```

## 2. Переменные окружения

Создай `projects/vr-cafe/.env`:

```bash
PORT=8007
# MONGODB_URI=                 # опционально, иначе постройки живут только в памяти
# TELEGRAM_BOT_TOKEN=
# TELEGRAM_CHAT_ID=
# PUBLIC_URL=https://cafe.robutpit.com
```

## 3. systemd-сервис

```ini
# /etc/systemd/system/vr-cafe.service
[Unit]
Description=VR Cafe Node.js app
After=network.target

[Service]
User=root
WorkingDirectory=/root/my-portfolio/projects/vr-cafe
EnvironmentFile=/root/my-portfolio/projects/vr-cafe/.env
ExecStart=/usr/bin/node server.js
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now vr-cafe
sudo systemctl status vr-cafe --no-pager -l | head -15
```

Порт `8007` — **обязательно** проверь заранее, что он свободен
(`sudo ss -tlnp | grep 800`). Карта портов на этом VPS
(актуально на 2026-08-15):

| Порт | Проект       |
|------|--------------|
| 8001 | b2b-platform |
| 8002 | istok        |
| 8003 | ai-tutor     |
| 8004 | balka        |
| 8005 | ferma        |
| 8006 | vr-shop      |
| 8007 | vr-cafe      |

При добавлении нового проекта — бери следующий свободный порт (8008) и
сверяйся с этой таблицей, а не угадывай.

## 4. nginx (обратный прокси + WebSocket для Socket.io/PeerJS)

```nginx
# /etc/nginx/sites-available/vr-cafe
server {
    listen 80;
    server_name cafe.robutpit.com;
    location / {
        proxy_pass http://127.0.0.1:8007;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

```bash
sudo ln -sf /etc/nginx/sites-available/vr-cafe /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

## 5. DNS + SSL

В Cloudflare DNS замени старую запись (если есть, CNAME на
`vr-cafe-a073.onrender.com`) на A-запись `cafe` → IP этого VPS. После того
как DNS обновится:

```bash
sudo certbot --nginx -d cafe.robutpit.com
```

## Обновление после изменений в коде

```bash
cd /root/my-portfolio
git pull origin main
cd projects/vr-cafe
npm install --production
systemctl restart vr-cafe
```
