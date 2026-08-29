"""Webhook Telegram-бота — привязка аккаунта к чату (см. app/telegram_bot.py)."""
import re
from datetime import datetime

from flask import Blueprint, abort, current_app, jsonify, request

from app import db, telegram_bot
from app.models import TelegramLink, TelegramLinkCode, User

bp = Blueprint("telegram", __name__)

LINK_CODE_RE = re.compile(r"^[0-9A-F]{8}$")


def send_message(chat_id, text):
    """Тонкая обёртка через модуль (не имя функции), чтобы патчинг
    app.telegram_bot.send_message в тестах действовал и здесь."""
    return telegram_bot.send_message(chat_id, text)


def _link_account(chat_id, username, user):
    existing_for_chat = TelegramLink.query.filter_by(telegram_chat_id=chat_id).first()
    if existing_for_chat is not None and existing_for_chat.user_id != user.id:
        db.session.delete(existing_for_chat)
        # flush() сразу — иначе при том же flush() ниже INSERT/UPDATE с тем
        # же telegram_chat_id уйдёт раньше этого DELETE (SQLAlchemy по
        # умолчанию шлёт insert/update перед delete) и упадёт по
        # unique-constraint telegram_links_telegram_chat_id_key.
        db.session.flush()

    link = TelegramLink.query.filter_by(user_id=user.id).first()
    if link is None:
        link = TelegramLink(user_id=user.id, telegram_chat_id=chat_id)
        db.session.add(link)
    else:
        link.telegram_chat_id = chat_id
    link.telegram_username = username
    link.notifications_enabled = True
    link.linked_at = datetime.utcnow()
    db.session.commit()

    send_message(chat_id, f"Аккаунт {user.email} привязан. Теперь сообщения с сайта «Исток» будут приходить сюда.")


def _handle_start(chat_id, username, token):
    if not token:
        send_message(
            chat_id,
            "Чтобы привязать аккаунт, откройте ссылку из раздела «Сообщения → Telegram» на сайте. "
            "Если вы уже писали этому боту раньше, ссылка может не сработать — тогда отправьте сюда "
            "код подтверждения, который тоже показан там.",
        )
        return

    user_id = telegram_bot.verify_link_token(token)
    if user_id is None:
        send_message(chat_id, "Ссылка для привязки устарела. Запросите новую на сайте — в разделе «Сообщения → Telegram».")
        return

    user = db.session.get(User, user_id)
    if user is None:
        send_message(chat_id, "Пользователь не найден.")
        return

    _link_account(chat_id, username, user)


def _handle_link_code(chat_id, username, code):
    record = TelegramLinkCode.query.filter_by(code=code).first()
    if record is None or datetime.utcnow() - record.created_at > telegram_bot.LINK_CODE_MAX_AGE:
        send_message(chat_id, "Код устарел или неверен. Обновите страницу «Сообщения → Telegram» — там будет новый.")
        return

    user = record.user
    db.session.delete(record)
    _link_account(chat_id, username, user)


@bp.route("/telegram/webhook/<secret>", methods=["POST"])
def webhook(secret):
    expected = current_app.config.get("TELEGRAM_WEBHOOK_SECRET")
    if not expected or secret != expected:
        abort(404)

    update = request.get_json(silent=True) or {}
    message = update.get("message") or {}
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    text = (message.get("text") or "").strip()

    if not chat_id:
        return jsonify({"ok": True})

    if text.startswith("/start"):
        parts = text.split(maxsplit=1)
        _handle_start(chat_id, chat.get("username"), parts[1] if len(parts) > 1 else None)
        return jsonify({"ok": True})

    bare_code = text.replace("/link", "", 1).strip().upper()
    if LINK_CODE_RE.match(bare_code):
        _handle_link_code(chat_id, chat.get("username"), bare_code)
        return jsonify({"ok": True})

    link = TelegramLink.query.filter_by(telegram_chat_id=chat_id).first()
    if link is None:
        send_message(
            chat_id,
            "Аккаунт ещё не привязан — перейдите по ссылке из раздела «Сообщения → Telegram» на сайте, "
            "либо отправьте сюда код подтверждения оттуда же.",
        )
    else:
        send_message(chat_id, "Это уведомления с сайта «Исток». Отвечать на сообщения пока можно только на сайте.")

    return jsonify({"ok": True})
