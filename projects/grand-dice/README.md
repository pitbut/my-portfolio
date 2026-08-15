# 🎲 Grand Dice Casino — модуль для сайта

Полноценное веб-казино с игрой в кости: регистрация, подтверждение email,
демо- и реальный баланс, вывод средств с OTP-подтверждением по email,
админ-панель для обработки заявок. Flask + SQLAlchemy + Flask-Migrate +
Flask-Login.

Приём/выдача реальных денег пока реализованы как заявки, которые обрабатывает
администратор вручную (в `/admin`) — интеграция с Click API запланирована
отдельно и подключится позже без изменения модели данных (заявки останутся
тем же механизмом, просто автоматизируется их закрытие).

## Игра

Классический "roll under/over": игрок выбирает порог 2-98 и направление.
Множитель выплаты = `(100 - house_edge) / шанс_выигрыша_в_процентах`
(`HOUSE_EDGE_PERCENT`, по умолчанию 1%). Бросок — криптостойкий RNG
(`secrets`) на сервере.

## Файлы

- `app/dice.py` — математика игры (бросок, шанс, множитель).
- `app/models.py` — User (email/пароль/балансы), GameRound (история ставок),
  WalletRequest (заявки на пополнение/вывод, включая OTP-поля).
- `app/routes/auth.py` — регистрация, вход, подтверждение email (по образцу
  проекта istok — Resend HTTP API, ссылка-токен через itsdangerous).
- `app/routes/game.py` — страница игры и обработка ставок (AJAX).
- `app/routes/wallet.py` — депозит/вывод, OTP на вывод.
- `app/routes/admin.py` — одобрение/отклонение заявок, список пользователей.

## Локальный запуск

```bash
python3 -m venv venv
venv/bin/pip install -r requirements.txt
cp .env.example .env    # заполнить SECRET_KEY, при желании ADMIN_EMAIL/ADMIN_PASSWORD
venv/bin/flask db upgrade
venv/bin/python seed.py  # создаст администратора, если задан ADMIN_EMAIL/ADMIN_PASSWORD
venv/bin/python run.py
```

Без `RESEND_API_KEY` письма (подтверждение регистрации, OTP на вывод) не
отправляются по-настоящему — их содержимое пишется в лог и показывается
во flash-сообщении на странице, чтобы разработка/тесты не блокировались.

## Шифрование номеров карт

`User.card_number` и `WalletRequest.card_number` хранятся в базе зашифрованными
(Fernet, `app/crypto.py`) — ключ берётся из `CARD_ENCRYPTION_KEY`. Без этого
ключа сохранить номер карты нельзя (ошибка, а не тихая запись в открытом
виде). Ключ сгенерировать так:

```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Ключ должен оставаться одним и тем же постоянно — его потеря делает уже
сохранённые номера карт нечитаемыми.
