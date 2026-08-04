"""Telegram-бот (модуль 7) — отправка уведомлений через Bot API и обработка
входящих команд через webhook.

Без TELEGRAM_BOT_TOKEN отправка не работает по-настоящему — сообщения
только логируются, как и с Resend/ImgBB выше по коду. Это единственный
канал, который реально нужно «подключить» ключом в конце: вся логика уже
на месте и заработает сразу, как только токен появится в переменных
окружения."""
import json
import urllib.error
import urllib.request

from flask import current_app, has_request_context, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/{method}"
LINK_SALT = "telegram-link"
LINK_TOKEN_MAX_AGE = 3600  # час на переход по deep-link'у из личного кабинета


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


def _call(method, payload):
    token = current_app.config.get("TELEGRAM_BOT_TOKEN")
    if not token:
        return None
    url = TELEGRAM_API_URL.format(token=token, method=method)
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST", headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode())
    except (urllib.error.URLError, OSError, ValueError):
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
    if not url:
        return None
    if url.startswith("http://") or url.startswith("https://"):
        return url
    if has_request_context():
        return request.url_root.rstrip("/") + url
    base = current_app.config.get("PUBLIC_BASE_URL")
    return (base.rstrip("/") + url) if base else url


def send_telegram_notification(user, title, body=None, url=None):
    """Единая точка входа, которую вызывает app.notify.notify() для ЛЮБОГО
    события платформы (модуль 2/5/6/8/9) — см. «10.4» в ТЗ."""
    from app.models import TelegramLink

    link = TelegramLink.query.filter_by(user_id=user.id, notifications_enabled=True).first()
    if link is None:
        return False

    text = title
    if body:
        text += "\n" + body
    absolute = _absolute_url(url)
    if absolute:
        text += "\n" + absolute

    return send_message(link.telegram_chat_id, text)
