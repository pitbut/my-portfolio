"""Личные сообщения — между пользователями и с администрацией.

У администратора нет своего аккаунта в users (вход по общему паролю), поэтому
"переписка с администрацией" — это сообщения, где sender/recipient_user_id
для стороны администрации равен NULL (см. app/models.py:Message)."""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import and_, or_

from app import db
from app.models import Message, User

bp = Blueprint("messages", __name__)

MAX_BODY_LENGTH = 4000


def _thread_query(user_id, other_id):
    return (
        Message.query.filter(
            or_(
                and_(Message.sender_user_id == user_id, Message.recipient_user_id == other_id),
                and_(Message.sender_user_id == other_id, Message.recipient_user_id == user_id),
            )
        )
        .order_by(Message.created_at.asc())
        .all()
    )


def _conversation_partners(user_id):
    """Список собеседников (None = администрация) с последним сообщением,
    отсортированный по свежести переписки."""
    all_messages = (
        Message.query.filter(
            or_(Message.sender_user_id == user_id, Message.recipient_user_id == user_id)
        )
        .order_by(Message.created_at.desc())
        .all()
    )

    partners = {}
    for m in all_messages:
        other_id = m.recipient_user_id if m.sender_user_id == user_id else m.sender_user_id
        if other_id not in partners:
            partners[other_id] = {"other_id": other_id, "last": m}

    for info in partners.values():
        info["unread"] = Message.query.filter_by(
            recipient_user_id=user_id, sender_user_id=info["other_id"], is_read=False
        ).count()
        info["other_user"] = db.session.get(User, info["other_id"]) if info["other_id"] else None

    return list(partners.values())


def _render_thread(other_id, other_user):
    thread = _thread_query(current_user.id, other_id)
    unread = [m for m in thread if m.recipient_user_id == current_user.id and not m.is_read]
    for m in unread:
        m.is_read = True
    if unread:
        db.session.commit()
    return render_template("messages/thread.html", thread=thread, other_id=other_id, other_user=other_user)


def _send(recipient_id, redirect_endpoint, **redirect_kwargs):
    if not current_user.email_confirmed:
        flash("Сначала подтвердите email, чтобы отправлять сообщения.", "error")
        return redirect(url_for(redirect_endpoint, **redirect_kwargs))

    body = (request.form.get("body") or "").strip()
    if not body:
        flash("Напишите текст сообщения.", "error")
    elif len(body) > MAX_BODY_LENGTH:
        flash("Сообщение слишком длинное.", "error")
    else:
        db.session.add(Message(sender_user_id=current_user.id, recipient_user_id=recipient_id, body=body))
        db.session.commit()

    return redirect(url_for(redirect_endpoint, **redirect_kwargs))


@bp.route("/")
@login_required
def inbox():
    partners = _conversation_partners(current_user.id)
    admin_unread = Message.query.filter_by(
        recipient_user_id=current_user.id, sender_user_id=None, is_read=False
    ).count()
    return render_template("messages/inbox.html", partners=partners, admin_unread=admin_unread)


@bp.route("/directory")
@login_required
def directory():
    users = User.query.filter(User.id != current_user.id).order_by(User.email).all()
    return render_template("messages/directory.html", users=users)


@bp.route("/admin")
@login_required
def thread_admin():
    return _render_thread(None, None)


@bp.route("/admin/send", methods=["POST"])
@login_required
def send_to_admin():
    return _send(None, "messages.thread_admin")


@bp.route("/user/<int:user_id>")
@login_required
def thread_user(user_id):
    if user_id == current_user.id:
        abort(404)
    other_user = User.query.get_or_404(user_id)
    return _render_thread(user_id, other_user)


@bp.route("/user/<int:user_id>/send", methods=["POST"])
@login_required
def send_to_user(user_id):
    if user_id == current_user.id:
        abort(404)
    User.query.get_or_404(user_id)
    return _send(user_id, "messages.thread_user", user_id=user_id)
