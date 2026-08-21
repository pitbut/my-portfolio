# Развёртывание сервера-релея на своём VPS

Предполагается VPS на Ubuntu/Debian с root- или sudo-доступом, и домен
(или поддомен, например `rynok.ваш-домен.ru`), у которого A-запись
указывает на IP вашего VPS.

Я не имею доступа к вашему VPS из этой сессии — эти шаги нужно выполнить
самостоятельно (или прислать мне доступ, если хотите, чтобы я сделал это
за вас). Когда сервер заработает, пришлите мне итоговый домен — я пересоберу
Android-приложение так, чтобы оно обращалось именно к нему.

## 1. DNS

Создайте A-запись `rynok.ваш-домен.ru → IP_ВАШЕГО_VPS` у регистратора домена.
Подождите, пока она разрешится (`dig rynok.ваш-домен.ru` должен показать ваш IP).

## 2. Node.js на VPS

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs
node -v   # должно быть 18+
```

## 3. Код сервера на VPS

```bash
sudo mkdir -p /opt/rynok
sudo chown $USER:$USER /opt/rynok
git clone https://github.com/pitbut/my-portfolio.git /tmp/my-portfolio
cp -r /tmp/my-portfolio/projects/rynok/server /opt/rynok/server
cd /opt/rynok/server
npm install --omit=dev
```

(Или просто скопируйте папку `projects/rynok/server` любым удобным
способом — scp, rsync и т.д. Главное, чтобы на VPS оказались `package.json`,
`package-lock.json` и `src/server.js`, после чего выполнить `npm install`.)

## 4. Systemd-сервис (автозапуск и перезапуск при падении)

```bash
sudo useradd --system --no-create-home --shell /usr/sbin/nologin rynok
sudo chown -R rynok:rynok /opt/rynok/server
sudo cp /opt/rynok/server/deploy/rynok-relay.service /etc/systemd/system/rynok-relay.service
sudo systemctl daemon-reload
sudo systemctl enable --now rynok-relay
sudo systemctl status rynok-relay   # должен быть active (running)
```

Проверка, что сервер отвечает локально:

```bash
curl http://127.0.0.1:3000/health
# {"ok":true,"families":0}
```

## 5. Nginx + HTTPS (обязательно для реального использования)

Android не даст подключиться по незашифрованному `ws://`/`http://` к
чужому домену (только к `10.0.2.2`/`localhost` для локальной отладки —
см. `android/app/src/main/res/xml/network_security_config.xml`). Поэтому
нужен HTTPS/WSS через Nginx с сертификатом Let's Encrypt.

```bash
sudo apt-get install -y nginx certbot python3-certbot-nginx

sudo cp /opt/rynok/server/deploy/nginx-rynok-relay.conf /etc/nginx/sites-available/rynok-relay
sudo sed -i 's/rynok.ВАШ-ДОМЕН.ru/rynok.ваш-домен.ru/' /etc/nginx/sites-available/rynok-relay
sudo ln -s /etc/nginx/sites-available/rynok-relay /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# certbot сам допишет TLS-блок в конфиг и настроит редирект с http на https
sudo certbot --nginx -d rynok.ваш-домен.ru
```

Проверка:

```bash
curl https://rynok.ваш-домен.ru/health
# {"ok":true,"families":0}
```

## 6. Фаервол

Если используете `ufw`:

```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

Порт 3000 наружу открывать не нужно — к нему обращается только Nginx
внутри сервера (`127.0.0.1:3000`).

## 7. Дальше

Как только `https://rynok.ваш-домен.ru/health` отвечает — сообщите мне этот
домен, и я пересоберу APK с адресом сервера
`wss://rynok.ваш-домен.ru/ws` и `https://rynok.ваш-домен.ru` вместо
адреса для локального эмулятора.

Обновления сервера в будущем — `git pull` (или повторное копирование)
в `/opt/rynok/server`, затем `sudo systemctl restart rynok-relay`.
