"""Админ-панель: обработка заявок на пополнение/вывод, обзор пользователей.

Админ — это обычный пользователь с флагом is_admin=True (создаётся через
seed.py), логинится через обычную форму входа.
"""
import os
from datetime import datetime, timedelta
from functools import wraps

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.models import GameRound, SupportMessage, User, WalletRequest
from app.uploads import save_support_photo, support_photo_path

bp = Blueprint("admin", __name__)

BLOCK_DURATIONS = {
    "1d": timedelta(days=1),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
}


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)

    return login_required(wrapped)


@bp.route("/")
@admin_required
def dashboard():
    pending = (
        WalletRequest.query.filter_by(status="pending")
        .order_by(WalletRequest.created_at.asc())
        .all()
    )
    # Комиссия казино, реально удержанная на ставках на реальные деньги:
    # сумма всех ставок минус сумма всех выплат (по проигрышам выплата 0,
    # по выигрышам — bet * multiplier, множитель уже учитывает house edge).
    real_bets = db.session.query(db.func.coalesce(db.func.sum(GameRound.bet_amount), 0)).filter(
        GameRound.mode == "real"
    ).scalar()
    real_payouts = db.session.query(db.func.coalesce(db.func.sum(GameRound.payout), 0)).filter(
        GameRound.mode == "real"
    ).scalar()

    stats = {
        "users": User.query.count(),
        "blocked_users": User.query.filter(
            db.or_(User.is_blocked.is_(True), User.blocked_until > datetime.utcnow())
        ).count(),
        "pending_requests": len(pending),
        "total_real_balance": db.session.query(db.func.coalesce(db.func.sum(User.real_balance), 0)).scalar(),
        "house_revenue": real_bets - real_payouts,
        "support_threads": db.session.query(SupportMessage.user_id).distinct().count(),
    }
    return render_template("admin/dashboard.html", pending=pending, stats=stats)


@bp.route("/users")
@admin_required
def users():
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin/users.html", users=all_users)


@bp.route("/requests/<int:request_id>/approve", methods=["POST"])
@admin_required
def approve_request(request_id):
    req = WalletRequest.query.get_or_404(request_id)
    if req.status != "pending":
        flash("Заявка уже обработана.", "error")
        return redirect(url_for("admin.dashboard"))

    if req.kind == "deposit":
        user = db.session.query(User).filter_by(id=req.user_id).with_for_update().one()
        user.real_balance += req.amount
    # для withdraw деньги уже списаны при подтверждении OTP — approve
    # означает "выплата отправлена", баланс не трогаем.

    req.status = "approved"
    req.admin_note = (request.form.get("note") or "").strip() or None
    req.processed_at = datetime.utcnow()
    req.processed_by_id = current_user.id
    db.session.commit()

    flash("Заявка одобрена.", "success")
    return redirect(url_for("admin.dashboard"))


@bp.route("/requests/<int:request_id>/reject", methods=["POST"])
@admin_required
def reject_request(request_id):
    req = WalletRequest.query.get_or_404(request_id)
    if req.status != "pending":
        flash("Заявка уже обработана.", "error")
        return redirect(url_for("admin.dashboard"))

    if req.kind == "withdraw":
        # Возвращаем зарезервированные при подтверждении OTP средства.
        user = db.session.query(User).filter_by(id=req.user_id).with_for_update().one()
        user.real_balance += req.amount

    req.status = "rejected"
    req.admin_note = (request.form.get("note") or "").strip() or None
    req.processed_at = datetime.utcnow()
    req.processed_by_id = current_user.id
    db.session.commit()

    flash("Заявка отклонена.", "info")
    return redirect(url_for("admin.dashboard"))


@bp.route("/users/<int:user_id>/block", methods=["POST"])
@admin_required
def block_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_admin:
        flash("Нельзя заблокировать администратора.", "error")
        return redirect(url_for("admin.users"))

    duration = request.form.get("duration")
    reason = (request.form.get("reason") or "").strip() or None

    if duration == "forever":
        user.is_blocked = True
        user.blocked_until = None
    elif duration in BLOCK_DURATIONS:
        user.blocked_until = datetime.utcnow() + BLOCK_DURATIONS[duration]
    else:
        flash("Некорректная длительность блокировки.", "error")
        return redirect(url_for("admin.users"))

    user.blocked_reason = reason
    db.session.commit()
    flash(f"Пользователь {user.email} заблокирован.", "success")
    return redirect(url_for("admin.users"))


@bp.route("/users/<int:user_id>/unblock", methods=["POST"])
@admin_required
def unblock_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_blocked = False
    user.blocked_until = None
    user.blocked_reason = None
    db.session.commit()
    flash(f"Пользователь {user.email} разблокирован.", "success")
    return redirect(url_for("admin.users"))


@bp.route("/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_admin:
        flash("Нельзя удалить администратора.", "error")
        return redirect(url_for("admin.users"))

    # Файлы фото на диске не удаляются каскадом БД — чистим их отдельно.
    for message in SupportMessage.query.filter_by(user_id=user.id):
        if message.photo_filename:
            path = support_photo_path(message.photo_filename)
            if os.path.exists(path):
                os.remove(path)

    email = user.email
    db.session.delete(user)
    db.session.commit()
    flash(f"Пользователь {email} удалён.", "success")
    return redirect(url_for("admin.users"))


@bp.route("/support")
@admin_required
def support_inbox():
    # Один тред на пользователя — берём последнее сообщение каждого треда
    # для сортировки по свежести и краткого превью.
    threads = (
        db.session.query(
            SupportMessage.user_id,
            db.func.max(SupportMessage.created_at).label("last_at"),
        )
        .group_by(SupportMessage.user_id)
        .order_by(db.desc("last_at"))
        .all()
    )
    users_by_id = {u.id: u for u in User.query.filter(
        User.id.in_([t.user_id for t in threads])
    ).all()}
    thread_list = [
        {"user": users_by_id[t.user_id], "last_at": t.last_at}
        for t in threads if t.user_id in users_by_id
    ]
    return render_template("admin/support_inbox.html", threads=thread_list)


@bp.route("/support/<int:user_id>", methods=["GET", "POST"])
@admin_required
def support_thread(user_id):
    user = User.query.get_or_404(user_id)

    if request.method == "POST":
        body = (request.form.get("body") or "").strip()
        photo = request.files.get("photo")
        try:
            photo_filename = save_support_photo(photo)
        except ValueError as exc:
            flash(str(exc), "error")
            return redirect(url_for("admin.support_thread", user_id=user.id))

        if not body and not photo_filename:
            flash("Напишите сообщение или приложите фото.", "error")
            return redirect(url_for("admin.support_thread", user_id=user.id))

        message = SupportMessage(
            user_id=user.id, sender_is_admin=True, body=body or None, photo_filename=photo_filename
        )
        db.session.add(message)
        db.session.commit()
        return redirect(url_for("admin.support_thread", user_id=user.id))

    messages = (
        SupportMessage.query.filter_by(user_id=user.id).order_by(SupportMessage.created_at.asc()).all()
    )
    return render_template("admin/support_thread.html", thread_user=user, messages=messages)


@bp.route("/support/message/<int:message_id>/delete", methods=["POST"])
@admin_required
def delete_support_message(message_id):
    message = SupportMessage.query.get_or_404(message_id)
    user_id = message.user_id

    if message.photo_filename:
        path = support_photo_path(message.photo_filename)
        if os.path.exists(path):
            os.remove(path)

    db.session.delete(message)
    db.session.commit()
    flash("Сообщение удалено.", "info")
    return redirect(url_for("admin.support_thread", user_id=user_id))
