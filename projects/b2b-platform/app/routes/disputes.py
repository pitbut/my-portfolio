"""Модуль 6 — арбитраж и медиация споров (сторона заказчика/исполнителя)."""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user

from app import db
from app.decorators import paywall_required
from app.models import Dispute, DisputeEvidence, DisputeMessage, Order, record_status_change
from app.notify import notify
from app.photos import upload_photo

bp = Blueprint("disputes", __name__)


def _order_parties(order):
    customer_user = order.customer.user
    executor_user = order.assignment.bid.executor.user if order.assignment else None
    return customer_user, executor_user


def _other_party(order, user):
    customer_user, executor_user = _order_parties(order)
    if user.id == customer_user.id:
        return executor_user
    return customer_user


def _is_party(order, user):
    customer_user, executor_user = _order_parties(order)
    return user.id == customer_user.id or (executor_user is not None and user.id == executor_user.id)


def _can_view_dispute(dispute):
    if current_user.role == "admin":
        return True
    return _is_party(dispute.order, current_user)


@bp.route("/orders/<int:order_id>/dispute/open", methods=["GET", "POST"])
@paywall_required
def open_dispute(order_id):
    order = db.session.get(Order, order_id)
    if order is None:
        abort(404)
    if not _is_party(order, current_user):
        abort(403)
    if order.status not in ("assigned", "in_progress", "completed"):
        flash("Спор можно открыть только по заказу, который назначен, в работе или завершён.", "error")
        return redirect(url_for("orders.order_detail", order_id=order.id))
    if order.dispute is not None:
        return redirect(url_for("disputes.dispute_detail", dispute_id=order.dispute.id))

    if request.method == "POST":
        reason_category = request.form.get("reason_category")
        description = (request.form.get("description") or "").strip()
        if reason_category not in ("defect", "delay", "quality", "price_dispute", "other") or not description:
            flash("Укажите причину и опишите ситуацию.", "error")
            return render_template("disputes/open.html", order=order)

        dispute = Dispute(
            order_id=order.id, opened_by_user_id=current_user.id,
            reason_category=reason_category, description=description, status="open",
        )
        db.session.add(dispute)
        record_status_change(order, "disputed", current_user)
        db.session.commit()

        other = _other_party(order, current_user)
        if other is not None:
            notify(
                other, "dispute_update", title=f"Открыт спор по заказу «{order.title}»",
                body="Ответьте на претензию и приложите доказательства.",
                url=url_for("disputes.dispute_detail", dispute_id=dispute.id),
            )
        flash("Спор открыт. Приложите доказательства — фото/видео подтвердят вашу позицию.", "info")
        return redirect(url_for("disputes.dispute_detail", dispute_id=dispute.id))

    return render_template("disputes/open.html", order=order)


@bp.route("/disputes/<int:dispute_id>", methods=["GET"])
@paywall_required
def dispute_detail(dispute_id):
    dispute = db.session.get(Dispute, dispute_id)
    if dispute is None:
        abort(404)
    if not _can_view_dispute(dispute):
        abort(403)
    is_admin = current_user.role == "admin"
    visible_messages = [m for m in dispute.messages if is_admin or not m.is_internal_admin_note]
    return render_template("disputes/detail.html", dispute=dispute, is_admin=is_admin, visible_messages=visible_messages)


@bp.route("/disputes/<int:dispute_id>/evidence", methods=["POST"])
@paywall_required
def add_evidence(dispute_id):
    dispute = db.session.get(Dispute, dispute_id)
    if dispute is None or not _can_view_dispute(dispute):
        abort(404)

    file_storage = request.files.get("file")
    url, error = upload_photo(file_storage)
    if error and not url:
        flash(error, "error")
        return redirect(url_for("disputes.dispute_detail", dispute_id=dispute.id))
    if not url:
        flash("Прикрепите файл доказательства.", "error")
        return redirect(url_for("disputes.dispute_detail", dispute_id=dispute.id))

    db.session.add(DisputeEvidence(
        dispute_id=dispute.id, uploaded_by_user_id=current_user.id, media_type="photo",
        file_url=url, comment=(request.form.get("comment") or "").strip() or None,
    ))
    if dispute.status == "open":
        dispute.status = "evidence_collection"
    db.session.commit()
    flash("Доказательство добавлено.", "success")
    return redirect(url_for("disputes.dispute_detail", dispute_id=dispute.id))


@bp.route("/disputes/<int:dispute_id>/message", methods=["POST"])
@paywall_required
def add_message(dispute_id):
    dispute = db.session.get(Dispute, dispute_id)
    if dispute is None or not _can_view_dispute(dispute):
        abort(404)

    text = (request.form.get("text") or "").strip()
    if not text:
        return redirect(url_for("disputes.dispute_detail", dispute_id=dispute.id))

    is_internal = current_user.role == "admin" and request.form.get("internal") == "1"
    db.session.add(DisputeMessage(dispute_id=dispute.id, sender_id=current_user.id, text=text, is_internal_admin_note=is_internal))
    db.session.commit()
    return redirect(url_for("disputes.dispute_detail", dispute_id=dispute.id))


@bp.route("/disputes/<int:dispute_id>/ready", methods=["POST"])
@paywall_required
def mark_ready(dispute_id):
    """Кнопка «Готово к рассмотрению» — сторона сообщает, что больше нечего
    приложить, спор можно передавать администратору."""
    dispute = db.session.get(Dispute, dispute_id)
    if dispute is None or not _is_party(dispute.order, current_user):
        abort(404)
    if dispute.status in ("open", "evidence_collection"):
        dispute.status = "in_review"
        db.session.commit()
        flash("Спор передан на рассмотрение администратору.", "info")
    return redirect(url_for("disputes.dispute_detail", dispute_id=dispute.id))
