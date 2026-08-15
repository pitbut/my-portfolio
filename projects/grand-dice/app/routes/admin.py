"""Админ-панель: обработка заявок на пополнение/вывод, обзор пользователей.

Админ — это обычный пользователь с флагом is_admin=True (создаётся через
seed.py), логинится через обычную форму входа.
"""
from datetime import datetime
from functools import wraps

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.models import User, WalletRequest

bp = Blueprint("admin", __name__)


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
    stats = {
        "users": User.query.count(),
        "pending_requests": len(pending),
        "total_real_balance": db.session.query(db.func.coalesce(db.func.sum(User.real_balance), 0)).scalar(),
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
