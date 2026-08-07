"""Модуль 3 — самостоятельное заполнение профиля заказчиком и исполнителем.

Ни один профиль не создаётся администратором: заказчик и исполнитель
заполняют свои карточки сами через эти формы сразу после регистрации
(и могут донаполнять их позже в любой момент).
"""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.decorators import role_required
from app.models import (
    City,
    ConstructorProfile,
    EquipmentType,
    ExecutorCapability,
    ExecutorEquipment,
    ExecutorProfile,
    Material,
    Region,
    ServiceCategory,
)

bp = Blueprint("profile", __name__)


def _to_int(value):
    value = (value or "").strip()
    return int(value) if value.isdigit() else None


def _to_float(value):
    value = (value or "").strip()
    try:
        return float(value) if value else None
    except ValueError:
        return None


def _regions():
    return Region.query.order_by(Region.name_ru).all()


@bp.route("/customer", methods=["GET", "POST"])
@role_required("customer")
def customer_edit():
    from app.models import CustomerProfile

    profile = current_user.customer_profile
    if profile is None:
        # На GET отдаём непривязанный к сессии объект только для рендера формы —
        # строка в БД не должна появляться, пока пользователь реально не сохранит
        # данные (иначе сам факт открытия страницы плодил бы пустые профили).
        profile = CustomerProfile(user_id=current_user.id)

    if request.method == "POST":
        if profile.id is None:
            db.session.add(profile)
        profile.kind = request.form.get("kind") if request.form.get("kind") in ("individual", "company") else None
        profile.display_name = (request.form.get("display_name") or "").strip() or None
        profile.stir_inn = (request.form.get("stir_inn") or "").strip() or None
        profile.region_id = _to_int(request.form.get("region_id"))
        profile.city_id = _to_int(request.form.get("city_id"))
        profile.address_text = (request.form.get("address_text") or "").strip() or None
        profile.latitude = _to_float(request.form.get("latitude"))
        profile.longitude = _to_float(request.form.get("longitude"))

        phone = (request.form.get("phone") or "").strip()
        if phone:
            current_user.phone = phone

        if profile.city_id and profile.region_id:
            city = db.session.get(City, profile.city_id)
            if city is None or city.region_id != profile.region_id:
                profile.city_id = None

        db.session.commit()

        if profile.is_complete:
            flash("Профиль заказчика сохранён и полностью заполнен.", "success")
        else:
            flash("Данные сохранены. Заполните обязательные поля (отмечены *), чтобы профиль стал полным.", "info")

        next_url = request.args.get("next")
        return redirect(next_url or url_for("profile.customer_edit"))

    return render_template("profile/customer_form.html", profile=profile, regions=_regions())


@bp.route("/constructor", methods=["GET", "POST"])
@role_required("constructor")
def constructor_edit():
    profile = current_user.constructor_profile
    if profile is None:
        profile = ConstructorProfile(user_id=current_user.id)

    if request.method == "POST":
        if profile.id is None:
            db.session.add(profile)
        profile.display_name = (request.form.get("display_name") or "").strip() or None
        profile.description = (request.form.get("description") or "").strip() or None
        profile.experience_years = _to_int(request.form.get("experience_years"))
        profile.portfolio_url = (request.form.get("portfolio_url") or "").strip() or None
        profile.price_note = (request.form.get("price_note") or "").strip() or None
        profile.region_id = _to_int(request.form.get("region_id"))
        profile.city_id = _to_int(request.form.get("city_id"))

        phone = (request.form.get("phone") or "").strip()
        if phone:
            current_user.phone = phone

        if profile.city_id and profile.region_id:
            city = db.session.get(City, profile.city_id)
            if city is None or city.region_id != profile.region_id:
                profile.city_id = None

        db.session.commit()

        if profile.is_complete:
            flash("Анкета конструктора сохранена и полностью заполнена — вы видны в каталоге «Конструкторы».", "success")
        else:
            flash("Данные сохранены. Заполните обязательные поля (отмечены *), чтобы анкета стала видна в каталоге.", "info")

        return redirect(url_for("profile.constructor_edit"))

    return render_template("profile/constructor_form.html", profile=profile, regions=_regions())


def _get_or_build_executor_profile():
    """Как и у заказчика: на GET отдаём непривязанный к сессии объект только
    для рендера формы, не создавая строку в БД раньше времени."""
    return current_user.executor_profile or ExecutorProfile(user_id=current_user.id)


@bp.route("/executor", methods=["GET", "POST"])
@role_required("executor")
def executor_edit():
    profile = _get_or_build_executor_profile()

    if request.method == "POST":
        if profile.id is None:
            db.session.add(profile)
        profile.org_type = request.form.get("org_type") if request.form.get("org_type") in ("master", "tsekh", "zavod") else None
        profile.display_name = (request.form.get("display_name") or "").strip() or None
        profile.description = (request.form.get("description") or "").strip() or None
        profile.stir_inn = (request.form.get("stir_inn") or "").strip() or None
        profile.region_id = _to_int(request.form.get("region_id"))
        profile.city_id = _to_int(request.form.get("city_id"))
        profile.address_text = (request.form.get("address_text") or "").strip() or None
        profile.latitude = _to_float(request.form.get("latitude"))
        profile.longitude = _to_float(request.form.get("longitude"))
        profile.service_radius_km = _to_int(request.form.get("service_radius_km")) or 50
        profile.has_design_engineer = request.form.get("has_design_engineer") == "1"

        phone = (request.form.get("phone") or "").strip()
        if phone:
            current_user.phone = phone

        if profile.city_id and profile.region_id:
            city = db.session.get(City, profile.city_id)
            if city is None or city.region_id != profile.region_id:
                profile.city_id = None

        db.session.commit()
        flash("Основные данные сохранены. Теперь заполните станочный парк и техвозможности ниже.", "success")
        return redirect(url_for("profile.executor_edit"))

    return render_template(
        "profile/executor_form.html",
        profile=profile,
        regions=_regions(),
        equipment_types=EquipmentType.query.order_by(EquipmentType.name_ru).all(),
        service_categories=ServiceCategory.query.order_by(ServiceCategory.name_ru).all(),
        materials=Material.query.order_by(Material.name_ru).all(),
    )


@bp.route("/executor/equipment/add", methods=["POST"])
@role_required("executor")
def executor_equipment_add():
    profile = current_user.executor_profile
    if profile is None:
        flash("Сначала сохраните основную информацию о цехе/заводе.", "error")
        return redirect(url_for("profile.executor_edit"))

    equipment_type_id = _to_int(request.form.get("equipment_type_id"))
    if not equipment_type_id or db.session.get(EquipmentType, equipment_type_id) is None:
        flash("Выберите тип оборудования из списка.", "error")
        return redirect(url_for("profile.executor_edit"))

    item = ExecutorEquipment(
        executor_id=profile.id,
        equipment_type_id=equipment_type_id,
        model_name=(request.form.get("model_name") or "").strip() or None,
        quantity=_to_int(request.form.get("quantity")) or 1,
        notes=(request.form.get("notes") or "").strip() or None,
    )
    db.session.add(item)
    db.session.commit()
    flash("Оборудование добавлено в станочный парк.", "success")
    return redirect(url_for("profile.executor_edit"))


@bp.route("/executor/equipment/<int:item_id>/delete", methods=["POST"])
@role_required("executor")
def executor_equipment_delete(item_id):
    profile = current_user.executor_profile
    if profile is None:
        abort(404)
    item = db.session.get(ExecutorEquipment, item_id)
    if item is None or item.executor_id != profile.id:
        abort(404)
    db.session.delete(item)
    db.session.commit()
    flash("Позиция удалена из станочного парка.", "info")
    return redirect(url_for("profile.executor_edit"))


@bp.route("/executor/capabilities", methods=["POST"])
@role_required("executor")
def executor_capabilities_save():
    profile = current_user.executor_profile
    if profile is None:
        flash("Сначала сохраните основную информацию о цехе/заводе.", "error")
        return redirect(url_for("profile.executor_edit"))

    capability = profile.capability
    if capability is None:
        capability = ExecutorCapability(executor_id=profile.id)
        db.session.add(capability)

    capability.max_length_mm = _to_int(request.form.get("max_length_mm"))
    capability.max_diameter_mm = _to_int(request.form.get("max_diameter_mm"))
    capability.max_width_mm = _to_int(request.form.get("max_width_mm"))
    capability.max_height_mm = _to_int(request.form.get("max_height_mm"))
    capability.max_weight_kg = _to_float(request.form.get("max_weight_kg"))

    service_ids = [int(v) for v in request.form.getlist("service_category_ids") if v.isdigit()]
    material_ids = [int(v) for v in request.form.getlist("material_ids") if v.isdigit()]

    capability.service_categories = ServiceCategory.query.filter(ServiceCategory.id.in_(service_ids)).all() if service_ids else []
    capability.materials = Material.query.filter(Material.id.in_(material_ids)).all() if material_ids else []

    db.session.commit()

    if profile.is_complete:
        from app.matching import match_new_executor_to_open_orders
        from app.subscriptions import TRIAL_DAYS, start_trial_if_needed

        started = start_trial_if_needed(profile)
        matched = match_new_executor_to_open_orders(profile)
        extra = f" Подобрано уже открытых заказов: {matched}." if matched else ""
        if started:
            flash(
                f"Техвозможности сохранены. Профиль полностью заполнен — включён бесплатный пробный период "
                f"на {TRIAL_DAYS} дней, заказы начнут подбираться автоматически.{extra}",
                "success",
            )
        else:
            flash(f"Техвозможности сохранены. Профиль полностью заполнен и участвует в подборе заказов.{extra}", "success")
    else:
        flash("Техвозможности сохранены.", "success")
    return redirect(url_for("profile.executor_edit"))


@bp.route("/cities/<int:region_id>.json")
@login_required
def cities_by_region(region_id):
    """Небольшой JSON-эндпоинт для клиентского каскадного списка городов —
    отдаёт города только выбранного региона, без загрузки всего справочника."""
    from flask import jsonify

    cities = City.query.filter_by(region_id=region_id).order_by(City.name_ru).all()
    from app.i18n import get_current_lang

    lang = get_current_lang()
    return jsonify([{"id": c.id, "name": c.name(lang)} for c in cities])
