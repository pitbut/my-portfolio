"""Простая админ-панель разбора споров (модуль 6).

Роль admin не выдаётся через самостоятельную регистрацию — только через
CLI-команду `flask create-admin <email> <password>` (см. README)."""
from datetime import datetime, timedelta

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user

from sqlalchemy.exc import IntegrityError

from app import db
from app.decorators import role_required
from app.models import (
    Dispute,
    Listing,
    ListingResponse,
    MaterialListing,
    MaterialListingResponse,
    Subscription,
    User,
    record_status_change,
)
from app.notify import notify
from app.routes.disputes import _order_parties

bp = Blueprint("admin", __name__)

OPEN_STATUSES = ("open", "evidence_collection", "in_review")
RESOLUTION_STATUSES = ("resolved_customer", "resolved_executor", "resolved_partial")
SUBSCRIPTION_PERIOD_DAYS = 30


@bp.route("/disputes")
@role_required("admin")
def disputes_list():
    open_disputes = Dispute.query.filter(Dispute.status.in_(OPEN_STATUSES)).order_by(Dispute.created_at).all()
    resolved_disputes = Dispute.query.filter(Dispute.status.notin_(OPEN_STATUSES)).order_by(Dispute.resolved_at.desc()).limit(30).all()
    return render_template("admin/disputes.html", open_disputes=open_disputes, resolved_disputes=resolved_disputes)


@bp.route("/disputes/<int:dispute_id>/resolve", methods=["POST"])
@role_required("admin")
def resolve_dispute(dispute_id):
    dispute = db.session.get(Dispute, dispute_id)
    if dispute is None:
        abort(404)

    resolution = request.form.get("resolution")
    resolution_text = (request.form.get("resolution_text") or "").strip()
    order_final_status = request.form.get("order_final_status")

    if resolution not in RESOLUTION_STATUSES or not resolution_text or order_final_status not in ("completed", "cancelled"):
        flash("Заполните решение, обоснование и итоговый статус заказа.", "error")
        return redirect(url_for("disputes.dispute_detail", dispute_id=dispute.id))

    dispute.status = resolution
    dispute.resolution_text = resolution_text
    dispute.resolved_at = datetime.utcnow()
    dispute.assigned_admin_id = current_user.id

    order = dispute.order
    record_status_change(order, order_final_status, current_user)
    db.session.commit()

    customer_user, executor_user = _order_parties(order)
    for party in (customer_user, executor_user):
        if party is not None:
            notify(
                party, "dispute_update", title=f"Решение по спору: «{order.title}»",
                body=resolution_text, url=url_for("disputes.dispute_detail", dispute_id=dispute.id),
            )

    flash("Решение вынесено, стороны уведомлены.", "success")
    return redirect(url_for("admin.disputes_list"))


@bp.route("/subscriptions")
@role_required("admin")
def subscriptions_list():
    pending = Subscription.query.filter_by(status="pending_payment").order_by(Subscription.started_at).all()
    return render_template("admin/subscriptions.html", pending=pending)


@bp.route("/subscriptions/<int:subscription_id>/approve", methods=["POST"])
@role_required("admin")
def approve_subscription(subscription_id):
    subscription = db.session.get(Subscription, subscription_id)
    if subscription is None:
        abort(404)

    subscription.status = "active"
    subscription.expires_at = datetime.utcnow() + timedelta(days=SUBSCRIPTION_PERIOD_DAYS)
    for payment in subscription.payments:
        if payment.status == "pending":
            payment.status = "succeeded"
            payment.provider_transaction_id = (request.form.get("reference") or "").strip() or None
    db.session.commit()

    notify(
        subscription.executor.user, "subscription_activated",
        title="Подписка активирована", body=f"Тариф «{subscription.plan.title}» действует до {subscription.expires_at.strftime('%d.%m.%Y')}.",
        url=url_for("settings.subscription_page"),
    )
    flash("Подписка активирована.", "success")
    return redirect(url_for("admin.subscriptions_list"))


@bp.route("/subscriptions/<int:subscription_id>/reject", methods=["POST"])
@role_required("admin")
def reject_subscription(subscription_id):
    subscription = db.session.get(Subscription, subscription_id)
    if subscription is None:
        abort(404)
    subscription.status = "cancelled"
    for payment in subscription.payments:
        if payment.status == "pending":
            payment.status = "failed"
    db.session.commit()
    flash("Заявка на подписку отклонена.", "info")
    return redirect(url_for("admin.subscriptions_list"))


@bp.route("/users")
@role_required("admin")
def users_list():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin/users.html", users=users)


@bp.route("/users/<int:user_id>")
@role_required("admin")
def user_detail(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        abort(404)
    listings = Listing.query.filter_by(author_id=user.id).order_by(Listing.created_at.desc()).all()
    material_listings = MaterialListing.query.filter_by(author_id=user.id).order_by(MaterialListing.created_at.desc()).all()
    return render_template("admin/user_detail.html", target_user=user, listings=listings, material_listings=material_listings)


@bp.route("/users/<int:user_id>/listings/<int:listing_id>/delete", methods=["POST"])
@role_required("admin")
def delete_user_listing(user_id, listing_id):
    listing = Listing.query.filter_by(id=listing_id, author_id=user_id).first()
    if listing is None:
        abort(404)
    db.session.delete(listing)
    db.session.commit()
    flash("Объявление (барахолка) удалено.", "success")
    return redirect(url_for("admin.user_detail", user_id=user_id))


@bp.route("/users/<int:user_id>/material-listings/<int:listing_id>/delete", methods=["POST"])
@role_required("admin")
def delete_user_material_listing(user_id, listing_id):
    listing = MaterialListing.query.filter_by(id=listing_id, author_id=user_id).first()
    if listing is None:
        abort(404)
    db.session.delete(listing)
    db.session.commit()
    flash("Объявление (материалы) удалено.", "success")
    return redirect(url_for("admin.user_detail", user_id=user_id))


@bp.route("/users/<int:user_id>/toggle-block", methods=["POST"])
@role_required("admin")
def toggle_block_user(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        abort(404)
    if user.role == "admin":
        flash("Нельзя заблокировать администратора.", "error")
        return redirect(url_for("admin.users_list"))

    user.is_blocked = not user.is_blocked
    db.session.commit()
    flash(f"{user.email}: {'заблокирован' if user.is_blocked else 'разблокирован'}.", "success")
    return redirect(url_for("admin.users_list"))


@bp.route("/users/<int:user_id>/delete", methods=["POST"])
@role_required("admin")
def delete_user(user_id):
    """Удаление устроено «честно»: если у пользователя уже есть связанные
    данные, которые нельзя молча стереть без потери чужой истории (заказы,
    сообщения, отзывы, споры и т.п.), база откажет по внешнему ключу — в этом
    случае лучше заблокировать аккаунт, а не удалять.

    Исключение — объявления (барахолка и материалы) и отклики на чужие
    объявления: это собственный контент пользователя, а не история сделки
    между сторонами, поэтому при удалении аккаунта его можно смело стирать
    вместе с пользователем, не дожидаясь ручной зачистки через /admin/users/<id>."""
    user = db.session.get(User, user_id)
    if user is None:
        abort(404)
    if user.role == "admin":
        flash("Нельзя удалить администратора.", "error")
        return redirect(url_for("admin.users_list"))

    email = user.email
    for listing in Listing.query.filter_by(author_id=user.id).all():
        db.session.delete(listing)
    for listing in MaterialListing.query.filter_by(author_id=user.id).all():
        db.session.delete(listing)
    ListingResponse.query.filter_by(from_user_id=user.id).delete(synchronize_session=False)
    MaterialListingResponse.query.filter_by(from_user_id=user.id).delete(synchronize_session=False)

    db.session.delete(user)
    try:
        db.session.commit()
        flash(f"{email}: аккаунт удалён.", "success")
    except IntegrityError:
        db.session.rollback()
        flash(
            f"{email}: не удалось удалить — с аккаунтом уже связаны данные "
            "(заказы, сообщения, отзывы и т.п.). Заблокируйте вместо удаления.",
            "error",
        )
    return redirect(url_for("admin.users_list"))
