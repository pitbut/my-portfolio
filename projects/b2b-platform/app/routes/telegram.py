"""Webhook Telegram-бота (модуль 7) — привязка аккаунта и базовые команды."""
from datetime import datetime

from flask import Blueprint, abort, current_app, jsonify, request

from app import db, telegram_bot
from app.models import Bid, Order, OrderMatch, TelegramLink, User
from app.subscriptions import current_subscription

bp = Blueprint("telegram", __name__)


def send_message(chat_id, text):
    """Тонкая обёртка через модуль (не имя функции), чтобы патчинг
    app.telegram_bot.send_message в тестах (и любая будущая замена
    транспорта) действовали здесь без дублирования логики."""
    return telegram_bot.send_message(chat_id, text)


def verify_link_token(token):
    return telegram_bot.verify_link_token(token)


def _handle_start(chat_id, username, token):
    if not token:
        send_message(chat_id, "Чтобы привязать аккаунт, откройте ссылку из раздела «Настройки» на сайте.")
        return

    user_id = verify_link_token(token)
    if user_id is None:
        send_message(chat_id, "Ссылка для привязки устарела. Запросите новую на сайте — в разделе «Настройки».")
        return

    user = db.session.get(User, user_id)
    if user is None:
        send_message(chat_id, "Пользователь не найден.")
        return

    existing_for_chat = TelegramLink.query.filter_by(telegram_chat_id=chat_id).first()
    if existing_for_chat is not None and existing_for_chat.user_id != user.id:
        db.session.delete(existing_for_chat)

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

    send_message(chat_id, f"Аккаунт {user.email} привязан. Теперь уведомления о заказах будут приходить сюда.")


def _handle_orders(chat_id, user):
    if user.role != "executor" or user.executor_profile is None:
        send_message(chat_id, "Команда доступна исполнителям — список заказов появляется в кабинете сайта.")
        return
    matches = (
        OrderMatch.query.filter_by(executor_id=user.executor_profile.id)
        .join(Order).filter(Order.status == "published")
        .order_by(OrderMatch.created_at.desc()).limit(5).all()
    )
    if not matches:
        send_message(chat_id, "Подходящих открытых заказов пока нет.")
        return
    lines = [f"• {m.order.title} ({m.order.service_category.name_ru})" for m in matches]
    send_message(chat_id, "Открытые заказы под ваш профиль:\n" + "\n".join(lines))


def _handle_mybids(chat_id, user):
    if user.role != "executor" or user.executor_profile is None:
        send_message(chat_id, "Команда доступна исполнителям.")
        return
    bids = Bid.query.filter_by(executor_id=user.executor_profile.id).order_by(Bid.created_at.desc()).limit(5).all()
    if not bids:
        send_message(chat_id, "У вас пока нет поданных ставок.")
        return
    lines = [f"• {b.order.title}: {b.price} {b.currency}, {b.status}" for b in bids]
    send_message(chat_id, "Ваши последние ставки:\n" + "\n".join(lines))


def _handle_subscription(chat_id, user):
    if user.role != "executor" or user.executor_profile is None:
        send_message(chat_id, "Подписка есть только у исполнителей.")
        return
    sub = current_subscription(user.executor_profile)
    if sub is None:
        send_message(chat_id, "Подписка не активна. Оформить можно в разделе «Подписка» на сайте.")
        return
    expires = sub.expires_at.strftime("%d.%m.%Y") if sub.expires_at else "бессрочно"
    send_message(chat_id, f"Тариф: {sub.plan.title}, статус: {sub.status}, действует до {expires}.")


@bp.route("/telegram/webhook/<secret>", methods=["POST"])
def webhook(secret):
    expected = current_app.config.get("TELEGRAM_WEBHOOK_SECRET")
    if not expected or secret != expected:
        abort(404)

    update = request.get_json(silent=True) or {}
    current_app.logger.info("Telegram webhook update: %s", update)
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

    link = TelegramLink.query.filter_by(telegram_chat_id=chat_id).first()
    if link is None:
        send_message(chat_id, "Аккаунт ещё не привязан — перейдите по ссылке из раздела «Настройки» на сайте.")
        return jsonify({"ok": True})

    user = link.user
    if text.startswith("/orders"):
        _handle_orders(chat_id, user)
    elif text.startswith("/mybids"):
        _handle_mybids(chat_id, user)
    elif text.startswith("/subscription"):
        _handle_subscription(chat_id, user)
    else:
        send_message(chat_id, "Команды: /orders — заказы, /mybids — мои ставки, /subscription — подписка.")

    return jsonify({"ok": True})
