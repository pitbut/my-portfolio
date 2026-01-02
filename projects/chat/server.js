// server.js - Пример сервера для Production версии чата
// Установите зависимости: npm install express socket.io cors

const express = require('express');
const http = require('http');
const socketIo = require('socket.io');
const cors = require('cors');

const app = express();
const server = http.createServer(app);
const io = socketIo(server, {
    cors: {
        origin: "*", // В production укажите конкретный домен
        methods: ["GET", "POST"]
    }
});

app.use(cors());
app.use(express.static('public')); // Папка с index.html

// Хранилище данных (в production используйте БД)
let users = []; // {id: socket.id, name: string, joinedAt: timestamp}
let messages = []; // {id: timestamp, author: string, text: string, timestamp: number}

// Максимум сообщений в истории
const MAX_MESSAGES = 100;

io.on('connection', (socket) => {
    console.log('Новое подключение:', socket.id);

    // Пользователь входит в чат
    socket.on('user:join', (data) => {
        const { name } = data;
        
        // Проверка уникальности имени
        const existingUser = users.find(u => u.name === name);
        if (existingUser) {
            socket.emit('error', { message: 'Это имя уже занято' });
            return;
        }

        // Добавляем пользователя
        const user = {
            id: socket.id,
            name: name,
            joinedAt: Date.now()
        };
        users.push(user);

        // Системное сообщение
        const systemMessage = {
            id: Date.now(),
            author: 'Система',
            text: `${name} присоединился к чату`,
            timestamp: Date.now(),
            isSystem: true
        };
        messages.push(systemMessage);

        // Отправляем подтверждение пользователю
        socket.emit('user:joined', { user });

        // Отправляем историю сообщений
        socket.emit('messages:history', { messages });

        // Уведомляем всех о новом пользователе
        io.emit('users:update', { users });
        io.emit('message:new', systemMessage);

        console.log(`${name} вошел в чат`);
    });

    // Новое сообщение
    socket.on('message:send', (data) => {
        const user = users.find(u => u.id === socket.id);
        if (!user) {
            socket.emit('error', { message: 'Сначала войдите в чат' });
            return;
        }

        const message = {
            id: Date.now(),
            author: user.name,
            text: data.text,
            timestamp: Date.now(),
            isSystem: false
        };

        messages.push(message);

        // Ограничиваем историю
        if (messages.length > MAX_MESSAGES) {
            messages = messages.slice(-MAX_MESSAGES);
        }

        // Отправляем всем
        io.emit('message:new', message);

        console.log(`${user.name}: ${data.text}`);
    });

    // Пользователь отключается
    socket.on('disconnect', () => {
        const user = users.find(u => u.id === socket.id);
        if (user) {
            // Удаляем пользователя
            users = users.filter(u => u.id !== socket.id);

            // Системное сообщение
            const systemMessage = {
                id: Date.now(),
                author: 'Система',
                text: `${user.name} покинул чат`,
                timestamp: Date.now(),
                isSystem: true
            };
            messages.push(systemMessage);

            // Уведомляем всех
            io.emit('users:update', { users });
            io.emit('message:new', systemMessage);

            console.log(`${user.name} вышел из чата`);
        }
    });

    // Обновление активности
    socket.on('user:activity', () => {
        const user = users.find(u => u.id === socket.id);
        if (user) {
            user.lastActive = Date.now();
        }
    });
});

// Очистка неактивных пользователей каждую минуту
setInterval(() => {
    const now = Date.now();
    const activeBefore = users.length;
    users = users.filter(u => (now - (u.lastActive || u.joinedAt)) < 300000); // 5 минут
    
    if (users.length !== activeBefore) {
        io.emit('users:update', { users });
        console.log(`Удалено неактивных пользователей: ${activeBefore - users.length}`);
    }
}, 60000);

const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
    console.log(`🚀 Сервер чата запущен на порту ${PORT}`);
    console.log(`📡 WebSocket сервер готов к подключениям`);
});

// Обработка ошибок
process.on('uncaughtException', (error) => {
    console.error('Критическая ошибка:', error);
});

process.on('unhandledRejection', (error) => {
    console.error('Необработанное отклонение промиса:', error);
});
