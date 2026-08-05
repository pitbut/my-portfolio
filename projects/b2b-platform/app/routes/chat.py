"""Модуль 11 — сообщения: диалог между любыми двумя пользователями
платформы (кооперация производителей, обращение к конструктору-фрилансеру,
вопрос по объявлению и т.п.), не привязанный к конкретному заказу."""
from datetime import datetime

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user

from app import db
from app.decorators import paywall_required
from app.models import Conversation, Message, User
from app.notify import notify

bp = Blueprint("chat", __name__, url_prefix="/messages")


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

    if request.method == "POST":
        body = (request.form.get("body") or "").strip()
        if not body:
            flash("Сообщение не может быть пустым.", "error")
            return redirect(url_for("chat.thread", user_id=user_id))

        conversation = _get_or_create_conversation(user_id)
        db.session.add(Message(conversation_id=conversation.id, sender_id=current_user.id, body=body))
        conversation.last_message_at = datetime.utcnow()
        db.session.commit()

        preview = body if len(body) <= 200 else body[:197] + "..."
        notify(
            other, "direct_message", title=f"Новое сообщение от {current_user.email}",
            body=preview, url=url_for("chat.thread", user_id=current_user.id),
        )
        return redirect(url_for("chat.thread", user_id=user_id))

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

    return render_template("chat/thread.html", other=other, conversation=conversation)
