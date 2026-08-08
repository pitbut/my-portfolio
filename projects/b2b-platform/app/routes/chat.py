"""Модуль 11 — сообщения: диалог между любыми двумя пользователями
платформы (кооперация производителей, обращение к конструктору-фрилансеру,
вопрос по объявлению и т.п.), не привязанный к конкретному заказу."""
from datetime import datetime

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user

from app import db
from app.decorators import paywall_required
from app.models import Conversation, Message, Order, User
from app.notify import notify

bp = Blueprint("chat", __name__, url_prefix="/messages")


def _order_involves(order, user_id):
    if order.customer and order.customer.user_id == user_id:
        return True
    return any(bid.executor.user_id == user_id for bid in order.bids)


def _order_context(user_id):
    """Заявку можно передать в чат через ?order_id=, чтобы собеседники видели,
    по какому именно номеру идёт речь (переписка общая на пару пользователей,
    даже если у них несколько заявок друг с другом одновременно). Показываем
    заявку только если оба — реальные стороны именно по ней (заказчик и
    заказчик/один из откликнувшихся исполнителей), иначе номер игнорируется."""
    order_id = request.args.get("order_id", type=int)
    if not order_id:
        return None
    order = db.session.get(Order, order_id)
    if order is None or not _order_involves(order, current_user.id) or not _order_involves(order, user_id):
        return None
    return order


def _find_conversation(user_id):
    return Conversation.query.filter(
        db.or_(
            db.and_(Conversation.user_a_id == current_user.id, Conversation.user_b_id == user_id),
            db.and_(Conversation.user_a_id == user_id, Conversation.user_b_id == current_user.id),
        )
    ).first()


def _get_or_create_conversation(user_id):
    conversation = _find_conversation(user_id)
    if conversation is None:
        user_a_id, user_b_id = sorted((current_user.id, user_id))
        conversation = Conversation(user_a_id=user_a_id, user_b_id=user_b_id)
        db.session.add(conversation)
        db.session.flush()
    return conversation


@bp.route("")
@paywall_required
def inbox():
    conversations = (
        Conversation.query.filter(
            db.or_(Conversation.user_a_id == current_user.id, Conversation.user_b_id == current_user.id)
        )
        .order_by(Conversation.last_message_at.desc())
        .all()
    )
    items = []
    for conversation in conversations:
        other = conversation.other_user(current_user)
        last_message = conversation.messages[-1] if conversation.messages else None
        unread = sum(1 for m in conversation.messages if m.sender_id != current_user.id and m.read_at is None)
        items.append({"conversation": conversation, "other": other, "last_message": last_message, "unread": unread})
    return render_template("chat/inbox.html", items=items)


@bp.route("/u/<int:user_id>", methods=["GET", "POST"])
@paywall_required
def thread(user_id):
    if user_id == current_user.id:
        flash("Нельзя написать самому себе.", "error")
        return redirect(url_for("chat.inbox"))
    other = db.session.get(User, user_id)
    if other is None:
        abort(404)

    order = _order_context(user_id)

    if request.method == "POST":
        body = (request.form.get("body") or "").strip()
        if not body:
            flash("Сообщение не может быть пустым.", "error")
            return redirect(url_for("chat.thread", user_id=user_id, order_id=order.id if order else None))

        conversation = _get_or_create_conversation(user_id)
        db.session.add(Message(conversation_id=conversation.id, sender_id=current_user.id, body=body))
        conversation.last_message_at = datetime.utcnow()
        db.session.commit()

        preview = body if len(body) <= 200 else body[:197] + "..."
        notify(
            other, "direct_message", title=f"Новое сообщение от {current_user.email}",
            body=preview, url=url_for("chat.thread", user_id=current_user.id, order_id=order.id if order else None),
        )
        return redirect(url_for("chat.thread", user_id=user_id, order_id=order.id if order else None))

    conversation = _find_conversation(user_id)
    if conversation is not None:
        now = datetime.utcnow()
        changed = False
        for m in conversation.messages:
            if m.sender_id != current_user.id and m.read_at is None:
                m.read_at = now
                changed = True
        if changed:
            db.session.commit()

    return render_template("chat/thread.html", other=other, conversation=conversation, order=order)
