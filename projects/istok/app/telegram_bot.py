"""Telegram-бот: отправка уведомлений о новых личных сообщениях через Bot
API и обработка входящих команд через webhook (привязка аккаунта).

Без TELEGRAM_BOT_TOKEN отправка не работает по-настоящему — сообщения
только логируются. Это единственное, что нужно "подключить" ключом —
вся остальная логика (привязка, уведомления) уже на месте и заработает
сразу, как только токен появится в переменных окружения."""
import secrets
from datetime import datetime, timedelta

import requests
from flask import current_app
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/{method}"
LINK_SALT = "telegram-link"
LINK_TOKEN_MAX_AGE = 3600  # час на переход по deep-link'у из «Сообщения → Telegram»
LINK_CODE_MAX_AGE = timedelta(minutes=30)


def _serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"])


def link_token_for(user):
    return _serializer().dumps(user.id, salt=LINK_SALT)


def verify_link_token(token):
    try:
        return _serializer().loads(token, salt=LINK_SALT, max_age=LINK_TOKEN_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None


def bot_deep_link(user):
    username = current_app.config.get("TELEGRAM_BOT_USERNAME")
    if not username:
        return None
    return f"https://t.me/{username}?start={link_token_for(user)}"


def link_code_for(user):
    """Короткий код для ручной отправки боту — переиспользует ещё не
    устаревший код, чтобы при повторном заходе на страницу он не менялся
    каждый раз."""
    from app import db
    from app.models import TelegramLinkCode

    existing = TelegramLinkCode.query.filter_by(user_id=user.id).first()
    if existing is not None and datetime.utcnow() - existing.created_at < LINK_CODE_MAX_AGE:
        return existing.code

    code = secrets.token_hex(4).upper()
    if existing is not None:
        # Обновляем ту же строку, а не удаляем и создаём новую: в одном
        # flush() SQLAlchemy по умолчанию шлёт INSERT раньше DELETE, так что
        # "удалить и вставить с тем же user_id" упадёт по unique-constraint.
        existing.code = code
        existing.created_at = datetime.utcnow()
    else:
        db.session.add(TelegramLinkCode(user_id=user.id, code=code))
    db.session.commit()
    return code


def _call(method, payload):
    token = current_app.config.get("TELEGRAM_BOT_TOKEN")
    if not token:
        return None
    url = TELEGRAM_API_URL.format(token=token, method=method)
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except (requests.RequestException, ValueError):
        current_app.logger.exception("Ошибка обращения к Telegram Bot API (%s).", method)
        return None


def send_message(chat_id, text):
    """Возвращает True, если сообщение реально отправлено."""
    if not current_app.config.get("TELEGRAM_BOT_TOKEN"):
        current_app.logger.warning("TELEGRAM_BOT_TOKEN не настроен — сообщение не отправлено: %s", text[:120])
        return False
    result = _call("sendMessage", {"chat_id": chat_id, "text": text})
    return bool(result and result.get("ok"))


def _absolute_url(url):
    """Уведомления всегда отправляются во время обработки запроса (при
    отправке сообщения через /messages/...), поэтому request доступен."""
    if not url:
        return None
    if url.startswith("http://") or url.startswith("https://"):
        return url
    from flask import request

    return request.url_root.rstrip("/") + url


def notify_new_message(recipient, sender_label, body, thread_url):
    """Шлёт уведомление о новом личном сообщении в привязанный Telegram-чат
    получателя. recipient=None (переписка с администрацией) обрабатывается
    отдельно через notify_admin() — у администрации нет своего user_id."""
    if recipient is None:
        return False
    link = getattr(recipient, "telegram_link", None)
    if link is None or not link.notifications_enabled:
        return False
    text = f"💧 Новое сообщение от {sender_label}:\n\n{body[:500]}"
    url = _absolute_url(thread_url)
    if url:
        text += f"\n\nОтветить: {url}"
    return send_message(link.telegram_chat_id, text)


def notify_admin(sender_label, body, thread_url):
    chat_id = current_app.config.get("ADMIN_TELEGRAM_CHAT_ID")
    if not chat_id:
        return False
    text = f"💧 Сообщение в поддержку от {sender_label}:\n\n{body[:500]}"
    url = _absolute_url(thread_url)
    if url:
        text += f"\n\nОтветить: {url}"
    return send_message(chat_id, text)
