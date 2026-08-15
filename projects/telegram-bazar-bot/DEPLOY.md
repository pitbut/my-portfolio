# Деплой на VPS — пошагово

Проект живёт внутри монорепозитория `my-portfolio`
(`projects/telegram-bazar-bot/`) — так же, как остальные проекты. При
переезде на другой VPS достаточно одного `git clone` всего `my-portfolio`.

БД — SQLite (`bazar.db`), хранится прямо в папке проекта на диске VPS,
переживает рестарты сервиса.

## 1. Первый запуск на сервере

```bash
cd /root/my-portfolio   # или куда склонирован монорепозиторий
git pull origin main

cd projects/telegram-bazar-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate
```

## 2. Переменные окружения

Создай `projects/telegram-bazar-bot/.env`:

```bash
BOT_TOKEN=<токен из @BotFather>
APP_URL=https://bazar.robutpit.com
```

## 3. systemd-сервис

```ini
# /etc/systemd/system/telegram-bazar-bot.service
[Unit]
Description=Telegram Bazar Bot (Flask)
After=network.target

[Service]
User=root
WorkingDirectory=/root/my-portfolio/projects/telegram-bazar-bot
EnvironmentFile=/root/my-portfolio/projects/telegram-bazar-bot/.env
ExecStart=/root/my-portfolio/projects/telegram-bazar-bot/venv/bin/gunicorn --bind 127.0.0.1:8008 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now telegram-bazar-bot
sudo systemctl status telegram-bazar-bot --no-pager -l | head -15
```

Порт `8008` — **обязательно** проверь заранее, что он свободен
(`sudo ss -tlnp | grep 800`). Карта портов на этом VPS
(актуально на 2026-08-15):

| Порт | Проект              |
|------|----------------------|
| 8001 | b2b-platform         |
| 8002 | istok                |
| 8003 | ai-tutor             |
| 8004 | balka                |
| 8005 | ferma                |
| 8006 | vr-shop              |
| 8007 | vr-cafe              |
| 8008 | telegram-bazar-bot   |

При добавлении нового проекта — бери следующий свободный порт (8009) и
сверяйся с этой таблицей, а не угадывай.

## 4. nginx

```nginx
# /etc/nginx/sites-available/telegram-bazar-bot
server {
    listen 80;
    server_name bazar.robutpit.com;
    location / {
        proxy_pass http://127.0.0.1:8008;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
sudo ln -sf /etc/nginx/sites-available/telegram-bazar-bot /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

## 5. DNS + SSL

В Cloudflare DNS добавь A-запись `bazar` → IP этого VPS. После того как
DNS обновится:

```bash
sudo certbot --nginx -d bazar.robutpit.com
```

## 6. Подключить вебхук у Telegram (один раз, после того как SSL уже работает)

```bash
curl "https://api.telegram.org/bot<ТВОЙ_BOT_TOKEN>/setWebhook?url=https://bazar.robutpit.com/webhook"
```

Должно прийти `{"ok":true,"result":true,...}`. Если бот раньше был
привязан к вебхуку на Render — этот шаг сам переключит вебхук на новый
адрес, отдельно отвязывать старый не нужно.

## Обновление после изменений в коде

```bash
cd /root/my-portfolio
git pull origin main
cd projects/telegram-bazar-bot
source venv/bin/activate && pip install -r requirements.txt && deactivate
systemctl restart telegram-bazar-bot
```
