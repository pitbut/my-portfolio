# 🚀 Инструкция по развертыванию чата на сервер

## Вариант 1: Локальное тестирование

### Шаг 1: Установка Node.js
Скачайте и установите Node.js с https://nodejs.org/ (LTS версия)

### Шаг 2: Установка зависимостей
```bash
cd svobodny-chat
npm install
```

### Шаг 3: Запуск сервера
```bash
npm start
```

Сервер запустится на http://localhost:3000

### Шаг 4: Тестирование
1. Откройте http://localhost:3000 в браузере
2. Откройте эту же ссылку в другом браузере или инкогнито-режиме
3. Войдите под разными именами
4. Отправляйте сообщения - они синхронизируются!

---

## Вариант 2: Развертывание на VPS (Ubuntu)

### Подключение к серверу
```bash
ssh user@your-server-ip
```

### Установка Node.js
```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs
```

### Загрузка проекта
```bash
cd /var/www
sudo git clone your-repo-url svobodny-chat
cd svobodny-chat
sudo npm install
```

### Установка PM2 (менеджер процессов)
```bash
sudo npm install -g pm2
```

### Запуск с PM2
```bash
pm2 start server.js --name "chat-server"
pm2 save
pm2 startup
```

### Настройка Nginx (обратный прокси)
```bash
sudo nano /etc/nginx/sites-available/chat
```

Добавьте конфигурацию:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

Активируйте конфигурацию:
```bash
sudo ln -s /etc/nginx/sites-available/chat /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Настройка SSL (Let's Encrypt)
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

---

## Вариант 3: Развертывание на Heroku (бесплатно)

### Шаг 1: Установка Heroku CLI
```bash
npm install -g heroku
heroku login
```

### Шаг 2: Создание приложения
```bash
cd svobodny-chat
heroku create your-chat-name
```

### Шаг 3: Настройка Procfile
Создайте файл `Procfile`:
```
web: node server.js
```

### Шаг 4: Deploy
```bash
git init
git add .
git commit -m "Initial commit"
git push heroku master
```

Приложение будет доступно на: https://your-chat-name.herokuapp.com

---

## Вариант 4: Firebase Hosting + Realtime Database

### Преимущества:
- ✅ Бесплатный tier
- ✅ Автоматическое масштабирование
- ✅ CDN по всему миру
- ✅ SSL из коробки

### Установка Firebase CLI
```bash
npm install -g firebase-tools
firebase login
firebase init
```

### Настройка Firebase
1. Выберите "Hosting" и "Realtime Database"
2. Создайте проект в Firebase Console
3. Настройте правила безопасности

### Deploy
```bash
firebase deploy
```

---

## Вариант 5: Docker контейнер

### Dockerfile
```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install --production
COPY . .
EXPOSE 3000
CMD ["node", "server.js"]
```

### Сборка и запуск
```bash
docker build -t chat-server .
docker run -p 3000:3000 -d chat-server
```

### Docker Compose
```yaml
version: '3.8'
services:
  chat:
    build: .
    ports:
      - "3000:3000"
    restart: always
    environment:
      - NODE_ENV=production
```

Запуск:
```bash
docker-compose up -d
```

---

## Мониторинг и логи

### PM2 логи
```bash
pm2 logs chat-server
pm2 monit
```

### Системные логи
```bash
journalctl -u nginx -f
tail -f /var/log/nginx/error.log
```

---

## Безопасность

### Рекомендации:
1. ✅ Используйте HTTPS (SSL)
2. ✅ Настройте CORS правильно
3. ✅ Добавьте rate limiting
4. ✅ Валидация входных данных
5. ✅ Регулярные обновления зависимостей
6. ✅ Файрволл настройте правильно

### Пример rate limiting (Express)
```bash
npm install express-rate-limit
```

```javascript
const rateLimit = require('express-rate-limit');

const limiter = rateLimit({
    windowMs: 15 * 60 * 1000, // 15 минут
    max: 100 // максимум 100 запросов
});

app.use(limiter);
```

---

## Масштабирование

### Redis для хранения сессий
```bash
npm install redis socket.io-redis
```

### Несколько инстансов с балансировкой
```bash
pm2 start server.js -i max
```

### База данных вместо памяти
Используйте MongoDB, PostgreSQL или MySQL для хранения сообщений

---

## Полезные команды

### Проверка портов
```bash
sudo netstat -tlnp | grep :3000
```

### Перезапуск сервера
```bash
pm2 restart chat-server
```

### Обновление кода
```bash
git pull origin main
npm install
pm2 restart chat-server
```

---

## Поддержка

Если возникли проблемы:
1. Проверьте логи: `pm2 logs`
2. Проверьте порты: `netstat -tlnp`
3. Проверьте firewall: `sudo ufw status`
4. Проверьте nginx: `sudo nginx -t`

**Сайт:** robutpit.com  
**Email:** support@robutpit.com
