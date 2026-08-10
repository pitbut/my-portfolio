"""Простая админ-панель разбора споров (модуль 6).

Роль admin не выдаётся через самостоятельную регистрацию — только через
CLI-команду `flask create-admin <email> <password>` (см. README)."""
from datetime import date, datetime, timedelta

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user

from sqlalchemy.exc import IntegrityError

from app import db
from app.decorators import role_required
from app.models import (
    City,
    ConstructorProfile,
    CustomerProfile,
    Dispute,
    ExecutorProfile,
    Listing,
    ListingCategory,
    ListingResponse,
    Material,
    MaterialForm,
    MaterialListing,
    MaterialListingResponse,
    Order,
    PageView,
    Region,
    ServiceCategory,
    Subscription,
    User,
    record_status_change,
)
from app.notify import notify
from app.routes.disputes import _order_parties

bp = Blueprint("admin", __name__)


def _to_int(value):
    value = (value or "").strip()
    return int(value) if value.isdigit() else None


def _to_float(value):
    value = (value or "").strip()
    try:
        return float(value) if value else None
    except ValueError:
        return None

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


ORDER_STATUSES = ("published", "assigned", "in_progress", "completed", "disputed", "cancelled")


@bp.route("/orders")
@role_required("admin")
def orders_list():
    """Лента всех заявок платформы — в отличие от orders.my_orders (только
    свои заявки заказчика), администратору нужен обзор всего рынка, а не
    пустой список (у админа нет своего CustomerProfile)."""
    status_filter = request.args.get("status")
    query = Order.query
    if status_filter in ORDER_STATUSES:
        query = query.filter_by(status=status_filter)
    orders = query.order_by(Order.created_at.desc()).limit(200).all()
    return render_template("admin/orders.html", orders=orders, status_filter=status_filter, order_statuses=ORDER_STATUSES)


@bp.route("/stats")
@role_required("admin")
def stats():
    """Счётчик посещений — считается по PageView (см. _count_page_view в
    app/__init__.py). Разбивку по дням считаем в Python, а не SQL-группировкой
    по дате: date()/DATE_TRUNC — по-разному работают в SQLite и PostgreSQL
    (тот же урок, что и с поиском — см. app/routes/search.py)."""
    from collections import Counter

    today = date.today()
    today_start = datetime(today.year, today.month, today.day)
    total_views = PageView.query.count()
    today_views = PageView.query.filter(PageView.created_at >= today_start).count()
    known_visitors = db.session.query(PageView.user_id).filter(PageView.user_id.isnot(None)).distinct().count()

    range_start_date = today - timedelta(days=13)
    range_start = datetime(range_start_date.year, range_start_date.month, range_start_date.day)
    recent_created_at = [
        row[0] for row in db.session.query(PageView.created_at).filter(PageView.created_at >= range_start).all()
    ]
    counts_by_date = Counter(ts.date() for ts in recent_created_at)
    daily = [
        {"date": range_start_date + timedelta(days=i), "count": counts_by_date.get(range_start_date + timedelta(days=i), 0)}
        for i in range(14)
    ]

    return render_template(
        "admin/stats.html", total_views=total_views, today_views=today_views,
        known_visitors=known_visitors, daily=daily,
    )


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
    customer_profile = CustomerProfile.query.filter_by(user_id=user.id).first()
    orders = (
        Order.query.filter_by(customer_id=customer_profile.id).order_by(Order.created_at.desc()).all()
        if customer_profile else []
    )
    profile = {
        "customer": customer_profile,
        "executor": user.executor_profile,
        "constructor": user.constructor_profile,
    }.get(user.role)
    return render_template(
        "admin/user_detail.html", target_user=user, listings=listings,
        material_listings=material_listings, orders=orders, profile=profile,
    )


@bp.route("/users/<int:user_id>/profile/edit", methods=["GET", "POST"])
@role_required("admin")
def edit_user_profile(user_id):
    """Позволяет администратору увидеть контакты пользователя и поправить
    анкету, если тот ввёл что-то неверно (опечатка в телефоне/адресе и т.п.) —
    сам администратор анкеты не заполняет, только исправляет уже введённые
    заказчиком/исполнителем/конструктором данные."""
    user = db.session.get(User, user_id)
    if user is None:
        abort(404)
    if user.role not in ("customer", "executor", "constructor"):
        abort(404)

    if user.role == "customer":
        profile = user.customer_profile or CustomerProfile(user_id=user.id)
    elif user.role == "executor":
        profile = user.executor_profile or ExecutorProfile(user_id=user.id)
    else:
        profile = user.constructor_profile or ConstructorProfile(user_id=user.id)

    if request.method == "POST":
        if profile.id is None:
            db.session.add(profile)

        user.phone = (request.form.get("phone") or "").strip() or None
        profile.display_name = (request.form.get("display_name") or "").strip() or None
        profile.region_id = _to_int(request.form.get("region_id"))
        profile.city_id = _to_int(request.form.get("city_id"))
        profile.latitude = _to_float(request.form.get("latitude"))
        profile.longitude = _to_float(request.form.get("longitude"))

        if profile.city_id and profile.region_id:
            city = db.session.get(City, profile.city_id)
            if city is None or city.region_id != profile.region_id:
                profile.city_id = None

        if user.role == "customer":
            profile.kind = request.form.get("kind") if request.form.get("kind") in ("individual", "company") else None
            profile.stir_inn = (request.form.get("stir_inn") or "").strip() or None
            profile.address_text = (request.form.get("address_text") or "").strip() or None
        elif user.role == "executor":
            profile.org_type = request.form.get("org_type") if request.form.get("org_type") in ("master", "tsekh", "zavod") else None
            profile.description = (request.form.get("description") or "").strip() or None
            profile.stir_inn = (request.form.get("stir_inn") or "").strip() or None
            profile.address_text = (request.form.get("address_text") or "").strip() or None
        else:
            profile.description = (request.form.get("description") or "").strip() or None
            profile.experience_years = _to_int(request.form.get("experience_years"))
            profile.portfolio_url = (request.form.get("portfolio_url") or "").strip() or None
            profile.price_note = (request.form.get("price_note") or "").strip() or None

        db.session.commit()
        flash(f"Профиль {user.email} обновлён.", "success")
        return redirect(url_for("admin.user_detail", user_id=user.id))

    return render_template(
        "admin/edit_profile.html", target_user=user, profile=profile,
        regions=Region.query.order_by(Region.name_ru).all(),
    )


@bp.route("/users/<int:user_id>/orders/<int:order_id>/edit", methods=["GET", "POST"])
@role_required("admin")
def edit_user_order(user_id, order_id):
    order = db.session.get(Order, order_id)
    if order is None or order.customer is None or order.customer.user_id != user_id:
        abort(404)

    if request.method == "POST":
        order.title = (request.form.get("title") or "").strip() or order.title
        order.description = (request.form.get("description") or "").strip() or order.description
        order_type = request.form.get("order_type")
        if order_type in ("manufacturing", "repair"):
            order.order_type = order_type
        service_category_id = _to_int(request.form.get("service_category_id"))
        if service_category_id:
            order.service_category_id = service_category_id
        order.material_id = _to_int(request.form.get("material_id"))
        order.dimensions_length_mm = _to_int(request.form.get("dimensions_length_mm"))
        order.dimensions_diameter_mm = _to_int(request.form.get("dimensions_diameter_mm"))
        order.dimensions_width_mm = _to_int(request.form.get("dimensions_width_mm"))
        order.dimensions_height_mm = _to_int(request.form.get("dimensions_height_mm"))
        order.weight_kg = _to_float(request.form.get("weight_kg"))
        order.budget_min = _to_float(request.form.get("budget_min"))
        order.budget_max = _to_float(request.form.get("budget_max"))
        region_id = _to_int(request.form.get("region_id"))
        if region_id:
            order.region_id = region_id
        order.city_id = _to_int(request.form.get("city_id"))
        order.address_text = (request.form.get("address_text") or "").strip() or None
        order.payment_methods = ",".join(request.form.getlist("payment_methods")) or None

        if order.city_id and order.region_id:
            city = db.session.get(City, order.city_id)
            if city is None or city.region_id != order.region_id:
                order.city_id = None

        deadline_raw = (request.form.get("deadline_date") or "").strip()
        if deadline_raw:
            try:
                order.deadline_date = date.fromisoformat(deadline_raw)
            except ValueError:
                pass
        else:
            order.deadline_date = None

        db.session.commit()
        flash(f"Заявка «{order.title}» обновлена.", "success")
        return redirect(url_for("admin.user_detail", user_id=user_id))

    return render_template(
        "admin/edit_order.html", target_user=order.customer.user, order=order,
        regions=Region.query.order_by(Region.name_ru).all(),
        service_categories=ServiceCategory.query.order_by(ServiceCategory.name_ru).all(),
        materials=Material.query.order_by(Material.name_ru).all(),
    )


@bp.route("/users/<int:user_id>/listings/<int:listing_id>/edit", methods=["GET", "POST"])
@role_required("admin")
def edit_user_listing(user_id, listing_id):
    listing = Listing.query.filter_by(id=listing_id, author_id=user_id).first()
    if listing is None:
        abort(404)

    if request.method == "POST":
        listing.title = (request.form.get("title") or "").strip() or listing.title
        listing.description = (request.form.get("description") or "").strip() or listing.description
        listing_intent = request.form.get("listing_intent")
        if listing_intent in ("sell", "buy"):
            listing.listing_intent = listing_intent
        category_id = _to_int(request.form.get("category_id"))
        if category_id:
            listing.category_id = category_id
        listing.condition = request.form.get("condition") if listing.listing_intent == "sell" else None
        listing.price = _to_float(request.form.get("price"))
        listing.currency = request.form.get("currency") or "UZS"
        listing.price_negotiable = request.form.get("price_negotiable") == "1"
        region_id = _to_int(request.form.get("region_id"))
        if region_id:
            listing.region_id = region_id
        listing.payment_methods = ",".join(request.form.getlist("payment_methods")) or None
        delivery = request.form.get("delivery")
        listing.delivery = delivery if delivery in ("none", "own", "yandex") else None

        db.session.commit()
        flash(f"Объявление «{listing.title}» обновлено.", "success")
        return redirect(url_for("admin.user_detail", user_id=user_id))

    return render_template(
        "admin/edit_listing.html", target_user=listing.author, listing=listing,
        regions=Region.query.order_by(Region.name_ru).all(),
        categories=ListingCategory.query.order_by(ListingCategory.name_ru).all(),
    )


@bp.route("/users/<int:user_id>/material-listings/<int:listing_id>/edit", methods=["GET", "POST"])
@role_required("admin")
def edit_user_material_listing(user_id, listing_id):
    listing = MaterialListing.query.filter_by(id=listing_id, author_id=user_id).first()
    if listing is None:
        abort(404)

    if request.method == "POST":
        listing.title = (request.form.get("title") or "").strip() or listing.title
        listing.description = (request.form.get("description") or "").strip() or listing.description
        listing_intent = request.form.get("listing_intent")
        if listing_intent in ("sell", "buy"):
            listing.listing_intent = listing_intent
        material_id = _to_int(request.form.get("material_id"))
        if material_id:
            listing.material_id = material_id
        listing.form_id = _to_int(request.form.get("form_id"))
        listing.quantity = _to_float(request.form.get("quantity"))
        listing.unit = request.form.get("unit") or None
        listing.price = _to_float(request.form.get("price"))
        listing.currency = request.form.get("currency") or "UZS"
        listing.price_negotiable = request.form.get("price_negotiable") == "1"
        region_id = _to_int(request.form.get("region_id"))
        if region_id:
            listing.region_id = region_id

        db.session.commit()
        flash(f"Объявление «{listing.title}» обновлено.", "success")
        return redirect(url_for("admin.user_detail", user_id=user_id))

    return render_template(
        "admin/edit_material_listing.html", target_user=listing.author, listing=listing,
        regions=Region.query.order_by(Region.name_ru).all(),
        materials=Material.query.order_by(Material.name_ru).all(),
        forms=MaterialForm.query.order_by(MaterialForm.name_ru).all(),
    )


@bp.route("/users/<int:user_id>/orders/<int:order_id>/delete", methods=["POST"])
@role_required("admin")
def delete_user_order(user_id, order_id):
    """Заявка (заказ) — не «объявление»: у неё может быть история ставок,
    назначение исполнителя, споры и отзывы. Поэтому здесь тоже честный отказ,
    а не тихая зачистка — для свежей заявки без откликов удаление пройдёт,
    для заказа в работе или со спором админ увидит явную причину отказа."""
    order = db.session.get(Order, order_id)
    if order is None or order.customer is None or order.customer.user_id != user_id:
        abort(404)

    title = order.title
    db.session.delete(order)
    try:
        db.session.commit()
        flash(f"Заявка «{title}» удалена.", "success")
    except IntegrityError:
        db.session.rollback()
        flash(
            f"Заявку «{title}» не удалось удалить — по ней уже есть история (ставки, отзывы, спор). "
            "Такую заявку можно только заблокировать вместе с аккаунтом, а не удалить.",
            "error",
        )
    return redirect(url_for("admin.user_detail", user_id=user_id))


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
    # PageView — просто лог посещений для статистики, не история сделки ни
    # с кем, поэтому тоже чистим вместе с пользователем, а не отказываем.
    PageView.query.filter_by(user_id=user.id).delete(synchronize_session=False)

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
