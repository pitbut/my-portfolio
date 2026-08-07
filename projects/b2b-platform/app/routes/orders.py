"""Модуль 2 — публикация заказа, автоподбор, лента исполнителя, аукцион ставок."""
from datetime import date, datetime, timedelta

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user

from app import db
from app.decorators import paywall_required, role_required
from app.matching import run_matching
from app.models import (
    Bid,
    Material,
    Order,
    OrderAssignment,
    OrderMedia,
    OrderMatch,
    Region,
    ServiceCategory,
    record_status_change,
)
from app.notify import notify
from app.photos import upload_photo

bp = Blueprint("orders", __name__)


def _to_int(value):
    value = (value or "").strip()
    return int(value) if value.lstrip("-").isdigit() else None


def _to_decimal(value):
    value = (value or "").strip()
    try:
        return float(value) if value else None
    except ValueError:
        return None


def _can_view_order(order):
    """Заявки — открытая лента: любой исполнитель может открыть и оценить
    любую заявку, не только «рекомендованные» подбором (см. executor_dashboard)."""
    if current_user.role == "admin":
        return True
    if current_user.role == "customer" and order.customer.user_id == current_user.id:
        return True
    if current_user.role == "executor":
        return True
    return False


@bp.route("/orders/new", methods=["GET", "POST"])
@role_required("customer")
def new_order():
    profile = current_user.customer_profile
    if profile is None or profile.id is None:
        flash("Сначала заполните профиль заказчика — без него нельзя опубликовать заказ.", "error")
        return redirect(url_for("profile.customer_edit", next=url_for("orders.new_order")))

    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        description = (request.form.get("description") or "").strip()
        order_type = request.form.get("order_type")
        service_category_id = _to_int(request.form.get("service_category_id"))
        region_id = _to_int(request.form.get("region_id"))

        errors = []
        if not title:
            errors.append("Укажите название заявки.")
        if not description:
            errors.append("Опишите, что нужно сделать.")
        if order_type not in ("manufacturing", "repair"):
            errors.append("Выберите тип заявки: изготовление или ремонт.")
        if not service_category_id:
            errors.append("Выберите категорию работ.")
        if not region_id:
            errors.append("Выберите регион.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template(
                "orders/new.html", regions=Region.query.order_by(Region.name_ru).all(),
                service_categories=ServiceCategory.query.order_by(ServiceCategory.name_ru).all(),
                materials=Material.query.order_by(Material.name_ru).all(), form=request.form,
            )

        auction_hours = _to_int(request.form.get("auction_hours")) or 48
        order = Order(
            customer_id=profile.id,
            title=title,
            description=description,
            content_language=current_user.preferred_language,
            order_type=order_type,
            service_category_id=service_category_id,
            material_id=_to_int(request.form.get("material_id")),
            dimensions_length_mm=_to_int(request.form.get("dimensions_length_mm")),
            dimensions_diameter_mm=_to_int(request.form.get("dimensions_diameter_mm")),
            dimensions_width_mm=_to_int(request.form.get("dimensions_width_mm")),
            dimensions_height_mm=_to_int(request.form.get("dimensions_height_mm")),
            weight_kg=_to_decimal(request.form.get("weight_kg")),
            budget_min=_to_decimal(request.form.get("budget_min")),
            budget_max=_to_decimal(request.form.get("budget_max")),
            region_id=region_id,
            city_id=_to_int(request.form.get("city_id")),
            address_text=(request.form.get("address_text") or "").strip() or None,
            latitude=_to_decimal(request.form.get("latitude")),
            longitude=_to_decimal(request.form.get("longitude")),
            auction_deadline_at=datetime.utcnow() + timedelta(hours=auction_hours),
            status="published",
        )
        deadline_raw = (request.form.get("deadline_date") or "").strip()
        if deadline_raw:
            try:
                order.deadline_date = date.fromisoformat(deadline_raw)
            except ValueError:
                pass

        db.session.add(order)
        db.session.flush()

        sort_order = 0
        for photo in request.files.getlist("photos")[:8]:
            url, error = upload_photo(photo)
            if url:
                db.session.add(OrderMedia(order_id=order.id, media_type="photo", file_url=url, sort_order=sort_order))
                sort_order += 1
            elif error:
                flash(error, "info")

        drawing = request.files.get("drawing")
        if drawing and drawing.filename:
            url, error = upload_photo(drawing)
            if url:
                db.session.add(OrderMedia(order_id=order.id, media_type="drawing", file_url=url, sort_order=sort_order))
                sort_order += 1
            elif error:
                flash(error, "info")

        video_url = (request.form.get("video_url") or "").strip()
        if video_url:
            db.session.add(OrderMedia(order_id=order.id, media_type="video", file_url=video_url, sort_order=sort_order))
            sort_order += 1

        document_url = (request.form.get("document_url") or "").strip()
        if document_url:
            db.session.add(OrderMedia(order_id=order.id, media_type="document", file_url=document_url, sort_order=sort_order))

        db.session.commit()

        matched = run_matching(order)
        if matched:
            flash(f"Заявка опубликована. Подобрано исполнителей: {matched}.", "success")
        else:
            flash("Заявка опубликована. Подходящих исполнителей пока не нашлось — мы оповестим вас, как только появятся.", "info")

        return redirect(url_for("orders.order_detail", order_id=order.id))

    return render_template(
        "orders/new.html", regions=Region.query.order_by(Region.name_ru).all(),
        service_categories=ServiceCategory.query.order_by(ServiceCategory.name_ru).all(),
        materials=Material.query.order_by(Material.name_ru).all(), form={},
    )


@bp.route("/orders")
@role_required("customer")
def my_orders():
    profile = current_user.customer_profile
    orders = Order.query.filter_by(customer_id=profile.id).order_by(Order.created_at.desc()).all() if profile and profile.id else []
    return render_template("orders/list.html", orders=orders)


@bp.route("/dashboard")
@role_required("executor")
def executor_dashboard():
    """Открытая лента: видно все опубликованные заявки (плюс свои
    заявки в работе/завершённые — если по ним была ставка), а не только те,
    что подобраны автоматически. Подобранные (совпадают станочный парк,
    габариты, регион, подписка) помечаются как «Рекомендуем» и идут первыми —
    так исполнитель без заполненного профиля тоже видит рынок, но подсказка,
    что стоит выгоднее откликнуться, остаётся."""
    profile = current_user.executor_profile

    query = Order.query
    if profile and profile.id:
        my_bid_order_ids = db.session.query(Bid.order_id).filter(Bid.executor_id == profile.id)
        orders = query.filter(db.or_(Order.status == "published", Order.id.in_(my_bid_order_ids))).order_by(Order.created_at.desc()).all()
    else:
        orders = query.filter(Order.status == "published").order_by(Order.created_at.desc()).all()

    matches_by_order = {}
    my_bid_by_order = {}
    if profile and profile.id:
        matches_by_order = {m.order_id: m for m in OrderMatch.query.filter_by(executor_id=profile.id).all()}
        my_bid_by_order = {b.order_id: b for b in Bid.query.filter_by(executor_id=profile.id).all()}

    orders.sort(key=lambda o: o.id not in matches_by_order)

    return render_template(
        "orders/dashboard.html", orders=orders,
        matches_by_order=matches_by_order, my_bid_by_order=my_bid_by_order,
    )


@bp.route("/orders/<int:order_id>")
@paywall_required
def order_detail(order_id):
    order = db.session.get(Order, order_id)
    if order is None:
        abort(404)
    if not _can_view_order(order):
        abort(403)

    my_bid = None
    if current_user.role == "executor" and current_user.executor_profile:
        my_bid = Bid.query.filter_by(order_id=order.id, executor_id=current_user.executor_profile.id).first()

    is_owner = current_user.role == "customer" and order.customer.user_id == current_user.id
    return render_template("orders/detail.html", order=order, my_bid=my_bid, is_owner=is_owner)


@bp.route("/orders/<int:order_id>/bid", methods=["POST"])
@role_required("executor")
def submit_bid(order_id):
    order = db.session.get(Order, order_id)
    if order is None:
        abort(404)
    executor = current_user.executor_profile
    if executor is None or not executor.is_complete:
        flash("Чтобы делать ставки, сначала полностью заполните профиль исполнителя.", "error")
        return redirect(url_for("profile.executor_edit"))
    if not order.is_open_for_bids:
        flash("Приём ставок по этому заказу уже закрыт.", "error")
        return redirect(url_for("orders.order_detail", order_id=order.id))

    price = _to_decimal(request.form.get("price"))
    lead_time_days = _to_int(request.form.get("lead_time_days"))
    if not price or not lead_time_days:
        flash("Укажите цену и срок выполнения.", "error")
        return redirect(url_for("orders.order_detail", order_id=order.id))

    bid = Bid.query.filter_by(order_id=order.id, executor_id=executor.id).first()
    is_new = bid is None
    if bid is None:
        bid = Bid(order_id=order.id, executor_id=executor.id)
        db.session.add(bid)
    bid.price = price
    bid.currency = request.form.get("currency") or "UZS"
    bid.lead_time_days = lead_time_days
    bid.comment = (request.form.get("comment") or "").strip() or None
    bid.status = "active"
    db.session.commit()

    flash("Ставка отправлена." if is_new else "Ставка обновлена.", "success")

    # исполнители, кого обошли по цене, узнают об этом сразу (см. ТЗ, модуль 7)
    cheaper = Bid.query.filter(
        Bid.order_id == order.id, Bid.status == "active", Bid.executor_id != executor.id, Bid.price > price,
    ).all()
    for outbid in cheaper:
        notify(
            outbid.executor.user, "outbid",
            title=f"Вас обошли по цене: {order.title}",
            body="Появилась более выгодная ставка — вы можете предложить новые условия, пока аукцион открыт.",
            url=f"/orders/{order.id}",
        )

    return redirect(url_for("orders.order_detail", order_id=order.id))


@bp.route("/orders/<int:order_id>/assign/<int:bid_id>", methods=["POST"])
@role_required("customer")
def assign_bid(order_id, bid_id):
    order = db.session.get(Order, order_id)
    if order is None or order.customer.user_id != current_user.id:
        abort(404)
    bid = db.session.get(Bid, bid_id)
    if bid is None or bid.order_id != order.id or bid.status != "active":
        abort(404)
    if order.assignment is not None:
        flash("Исполнитель уже выбран.", "error")
        return redirect(url_for("orders.order_detail", order_id=order.id))

    assignment = OrderAssignment(
        order_id=order.id, bid_id=bid.id, agreed_price=bid.price,
        agreed_deadline=date.today() + timedelta(days=bid.lead_time_days),
    )
    db.session.add(assignment)
    bid.status = "accepted"
    record_status_change(order, "assigned", current_user)

    for other in order.bids:
        if other.id != bid.id and other.status == "active":
            other.status = "rejected"
            notify(
                other.executor.user, "bid_rejected", title=f"Заказ выбрал другого исполнителя: {order.title}",
                body="Спасибо за участие — в этот раз заказчик выбрал другое предложение.",
                url=f"/orders/{order.id}",
            )

    db.session.commit()

    notify(
        bid.executor.user, "bid_accepted", title=f"Ваша ставка принята: {order.title}",
        body=f"Согласованная цена: {bid.price} {bid.currency}. Срок: {bid.lead_time_days} дн.",
        url=f"/orders/{order.id}",
    )
    flash("Исполнитель выбран, заказ передан в работу.", "success")
    return redirect(url_for("orders.order_detail", order_id=order.id))


@bp.route("/orders/<int:order_id>/start", methods=["POST"])
@role_required("executor")
def start_order(order_id):
    order = db.session.get(Order, order_id)
    if order is None or not order.assignment or order.assignment.bid.executor_id != current_user.executor_profile.id:
        abort(404)
    if order.status != "assigned":
        flash("Заказ уже в другой стадии.", "error")
        return redirect(url_for("orders.order_detail", order_id=order.id))
    record_status_change(order, "in_progress", current_user)
    db.session.commit()
    flash("Заказ отмечен как «в работе».", "success")
    return redirect(url_for("orders.order_detail", order_id=order.id))


@bp.route("/orders/<int:order_id>/complete", methods=["POST"])
@role_required("customer")
def complete_order(order_id):
    order = db.session.get(Order, order_id)
    if order is None or order.customer.user_id != current_user.id:
        abort(404)
    if order.status != "in_progress":
        flash("Подтвердить приёмку можно только для заказа в работе.", "error")
        return redirect(url_for("orders.order_detail", order_id=order.id))
    record_status_change(order, "completed", current_user)
    order.assignment.completed_at = datetime.utcnow()
    db.session.commit()

    notify(
        order.assignment.bid.executor.user, "order_completed",
        title=f"Заказ принят заказчиком: {order.title}", body="Можно оставить отзыв друг о друге.",
        url=f"/orders/{order.id}",
    )
    flash("Заказ завершён. Теперь можно оставить отзыв.", "success")
    return redirect(url_for("orders.order_detail", order_id=order.id))
