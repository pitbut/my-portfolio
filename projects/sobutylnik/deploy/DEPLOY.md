# Деплой «Собутыльника» на свой VPS

Инструкция рассчитана на Ubuntu/Debian с уже работающим nginx (на котором,
предположительно, крутится ваш текущий сайт) и Python 3.11+. Всё, что
ниже, **добавляет новые файлы и новый systemd-юнит, не трогая ничего
существующего**. Каждый шаг с изменением системных файлов — обратимый.

## 0. Перед началом — подстраховка

```bash
# Бэкап текущих конфигов nginx, на всякий случай (можно потом удалить)
sudo cp -r /etc/nginx/sites-available /etc/nginx/sites-available.backup-$(date +%F)

# Убедитесь, что порт 8014 никем не занят (если занят — возьмите другой,
# например 8002, и замените везде ниже, включая nginx-конфиг)
sudo ss -ltnp | grep 8014 || echo "порт свободен"
```

## 1. DNS

Добавьте A-запись для нового поддомена (например `sobutylnik.ваш-домен.ru`),
указывающую на IP вашего VPS — у регистратора/DNS-провайдера, отдельной
записью, никакие существующие записи не трогая.

## 2. Системный пользователь и код

```bash
sudo useradd --system --create-home --shell /usr/sbin/nologin sobutylnik

# Клонируем репозиторий целиком (внутри — папка projects/sobutylnik,
# ровно та, на которую смотрят systemd-юнит и nginx-конфиг ниже).
# Код пока не влит в main — берём прямо ветку с изменениями; после того
# как смержите PR, здесь можно будет переключиться на main и дальше
# обновляться шагом «Обновление после новых коммитов» ниже.
sudo -u sobutylnik git clone --branch claude/virtual-drinking-buddy-site-cmrfx6 \
    https://github.com/pitbut/my-portfolio.git /opt/sobutylnik
cd /opt/sobutylnik

cd /opt/sobutylnik/projects/sobutylnik
sudo -u sobutylnik python3 -m venv venv
sudo -u sobutylnik ./venv/bin/pip install -r requirements.txt
```

## 3. Настройки (.env)

```bash
sudo -u sobutylnik cp .env.example .env
sudo -u sobutylnik nano .env
```

Заполните как минимум:

- `SECRET_KEY` — случайная строка (`python3 -c "import secrets; print(secrets.token_hex(32))"`)
- `FLASK_CONFIG=production`
- `DATABASE_URL` — например `postgresql://sobutylnik:пароль@localhost:5432/sobutylnik` (см. шаг 3а) либо оставьте пустым для SQLite (годится для теста, для реальной нагрузки — не рекомендуется)
- `ANTHROPIC_API_KEY` — ключ с console.anthropic.com
- `ADMIN_PASSWORD` — **новый** пароль администратора (раз старый один раз попадал в переписку открытым текстом — задайте другой)
- `RESEND_API_KEY` + `MAIL_DEFAULT_SENDER` — для писем подтверждения регистрации (необязательно, без них ссылка подтверждения просто пишется в лог)
- `IMGBB_API_KEY` — для сохранения фото/файлов (необязательно)

Важно про формат `.env` для systemd: **без кавычек** вокруг значений и без
слова `export` — `EnvironmentFile=` в юните читает файл построчно как
`КЛЮЧ=значение`, кавычки попадут в значение буквально.

```bash
sudo chmod 600 .env
```

### 3а. (если используете PostgreSQL) — своя БД, не трогающая существующую

```bash
sudo -u postgres psql -c "CREATE USER sobutylnik WITH PASSWORD 'придумайте-пароль';"
sudo -u postgres psql -c "CREATE DATABASE sobutylnik OWNER sobutylnik;"
```

Отдельная БД и отдельный пользователь БД — существующие базы других
сайтов никак не задействованы.

## 4. Миграции и первый запуск вручную (проверка перед systemd)

```bash
cd /opt/sobutylnik/projects/sobutylnik
sudo -u sobutylnik ./venv/bin/flask db upgrade
sudo -u sobutylnik ./venv/bin/python seed.py
sudo -u sobutylnik ./venv/bin/gunicorn run:app --bind 127.0.0.1:8014
```

Откройте в другом терминале `curl -I http://127.0.0.1:8014/` — должен
прийти `200 OK`. Остановите (Ctrl+C) — дальше это возьмёт на себя systemd.

## 5. systemd-юнит

```bash
sudo cp deploy/sobutylnik.service /etc/systemd/system/sobutylnik.service
sudo systemctl daemon-reload
sudo systemctl enable --now sobutylnik
sudo systemctl status sobutylnik   # должно быть active (running)
journalctl -u sobutylnik -f        # логи, если что-то не так — Ctrl+C для выхода
```

Это **новый** юнит с уникальным именем — не пересекается ни с какими
другими сервисами на машине.

## 6. nginx — новый файл, существующие не редактируем

```bash
sudo cp deploy/nginx-sobutylnik.conf /etc/nginx/sites-available/sobutylnik.conf
sudo nano /etc/nginx/sites-available/sobutylnik.conf
# замените SOBUTYLNIK.VASH-DOMEN.RU на реальный поддомен из шага 1

sudo ln -s /etc/nginx/sites-available/sobutylnik.conf /etc/nginx/sites-enabled/sobutylnik.conf

# КЛЮЧЕВОЙ шаг безопасности: проверка синтаксиса ПЕРЕД применением.
# Если тут ошибка — nginx её покажет и НИЧЕГО не изменится, текущий
# сайт продолжит работать как работал.
sudo nginx -t

# reload, а не restart — применяет новый конфиг, не разрывая уже
# открытые соединения к вашему текущему сайту
sudo systemctl reload nginx
```

Если `nginx -t` ругается — не делайте `reload`, пока ошибка не
исправлена; старый конфиг при этом продолжает действовать как ни в чём
не бывало.

## 7. SSL-сертификат для нового поддомена

```bash
sudo certbot --nginx -d sobutylnik.ваш-домен.ru
```

Certbot допишет блок `listen 443` прямо в `sobutylnik.conf` и настроит
редирект с 80 на 443 — только в этом файле, сертификаты и конфиги других
доменов на сервере не затрагивает.

## 8. Проверка

```bash
curl -I https://sobutylnik.ваш-домен.ru/
```

Должен прийти `200 OK`. Откройте в браузере, попробуйте
регистрацию → подтверждение (или лог, если Resend не настроен) →
`/admin` с новым паролем.

## Обновление после новых коммитов

```bash
cd /opt/sobutylnik
sudo -u sobutylnik git pull
cd projects/sobutylnik
sudo -u sobutylnik ./venv/bin/pip install -r requirements.txt
sudo systemctl restart sobutylnik   # применит новый код + прогонит миграции (ExecStartPre)
```

Затрагивает только сервис `sobutylnik` — на остальной сервер и другие
сайты не влияет.

## Если что-то пошло не так

- **Сайт с юнитом не поднимается** — `journalctl -u sobutylnik -n 50`,
  проверить `.env` (особенно `DATABASE_URL`/`ANTHROPIC_API_KEY`).
- **nginx не перезагружается / 502 Bad Gateway** — `sudo nginx -t`
  покажет синтаксическую ошибку; 502 обычно значит, что
  `systemctl status sobutylnik` не `active` — юнит не слушает порт 8014.
- **Откатить nginx** — удалить симлинк
  `sudo rm /etc/nginx/sites-enabled/sobutylnik.conf`, затем
  `sudo nginx -t && sudo systemctl reload nginx` — существующий сайт
  как и раньше не затрагивался, откатывать там нечего.
- **Полностью остановить/удалить** — `sudo systemctl disable --now sobutylnik`,
  удалить `/etc/systemd/system/sobutylnik.service`,
  `sudo systemctl daemon-reload`, удалить nginx-файл и симлинк как выше.
