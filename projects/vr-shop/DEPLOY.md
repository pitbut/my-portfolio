# Деплой на VPS — пошагово

Проект живёт внутри монорепозитория `my-portfolio`
(`projects/vr-shop/backend/`) — так же, как `b2b-platform` и `ai-tutor`.
При переезде на другой VPS достаточно одного `git clone` всего
`my-portfolio`, а не отдельных репозиториев на каждый проект.

БД по умолчанию — SQLite (`backend/shop.db`), файл переживает рестарты
сервиса, но не переживает переезд на новый диск/сервер вручную — если
нужна отдельная Postgres-база, задай `DATABASE_URL` (см. ниже). Загруженные
продавцом модели по умолчанию складываются на локальный диск
(`backend/uploads/`) — для защиты от потери при переносе можно подключить
Cloudflare R2 через переменные `R2_*`.

## 1. Первый запуск на сервере

```bash
cd /root/my-portfolio   # или куда склонирован монорепозиторий
git pull origin main

cd projects/vr-shop/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate
```

## 2. Переменные окружения

Создай `projects/vr-shop/backend/.env`:

```bash
SECRET_KEY=$(openssl rand -hex 32)
# DATABASE_URL=postgresql://user:pass@localhost:5432/vr_shop   # опционально, иначе SQLite
# R2_ACCOUNT_ID=
# R2_ACCESS_KEY=
# R2_SECRET_KEY=
# R2_BUCKET=
# R2_PUBLIC_URL=
```

## 3. systemd-сервис

```ini
# /etc/systemd/system/vr-shop.service
[Unit]
Description=VR Shop Flask app
After=network.target

[Service]
User=root
WorkingDirectory=/root/my-portfolio/projects/vr-shop/backend
EnvironmentFile=/root/my-portfolio/projects/vr-shop/backend/.env
ExecStart=/root/my-portfolio/projects/vr-shop/backend/venv/bin/gunicorn --worker-class gthread --threads 4 -w 1 --bind 127.0.0.1:8002 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now vr-shop
sudo systemctl status vr-shop --no-pager -l | head -15
```

Порт `8002` — **обязательно** проверь заранее, что он свободен
(`sudo ss -tlnp | grep 800`), прежде чем создавать сервис: на этом VPS
`b2b-platform` уже занимает `127.0.0.1:8001` — если два systemd-сервиса
проксируются на один и тот же порт, nginx будет отдавать ответы того
сервиса, который реально держит порт, независимо от домена (именно так
`shop.robutpit.com` при первой попытке показывал b2b-platform).

## 4. nginx (обратный прокси + вебсокеты для Flask-SocketIO)

```nginx
# /etc/nginx/sites-available/vr-shop
server {
    listen 80;
    server_name shop.robutpit.com;
    location / {
        proxy_pass http://127.0.0.1:8002;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

```bash
sudo ln -sf /etc/nginx/sites-available/vr-shop /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

## 5. DNS + SSL

В Cloudflare DNS замени старую запись (CNAME на `vr-shop.onrender.com`) на
A-запись `shop` → IP этого VPS. После того как DNS обновится:

```bash
sudo certbot --nginx -d shop.robutpit.com
```

## 6. Первичные тестовые данные

При первом старте `app.py` сам создаёт таблицы (`db.create_all()`) и
наполняет 2 тестовых магазина (`seed_data.py`), если база пустая — ничего
запускать вручную не нужно.

## Обновление после изменений в коде

Используй `deploy.sh` из этой же папки:

```bash
/root/my-portfolio/projects/vr-shop/deploy.sh
```
