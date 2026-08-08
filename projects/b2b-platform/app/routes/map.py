"""Модуль 4 — интерактивная карта Узбекистана и гео-поиск исполнителей."""
from flask import Blueprint, jsonify, render_template, request, url_for
from flask_login import login_required

from app.decorators import paywall_required
from app.geo import haversine_km
from app.models import ConstructorProfile, ExecutorProfile, Listing, Region, ServiceCategory, User

bp = Blueprint("map", __name__)


def _visible_executors_query():
    """Профиль виден на карте/в геопоиске только когда действительно
    заполнен (есть координаты, оборудование, техвозможности) — иначе
    показывать нечего и незачем. Плюс User.role == 'executor': если
    пользователь переключился на другую роль в настройках, его старая
    анкета исполнителя остаётся в базе, но с карты пропадает."""
    return ExecutorProfile.query.join(User, ExecutorProfile.user_id == User.id).filter(
        User.role == "executor",
        ExecutorProfile.latitude.isnot(None),
        ExecutorProfile.longitude.isnot(None),
        ExecutorProfile.display_name.isnot(None),
    )


def _executor_payload(executor):
    services = executor.capability.service_categories if executor.capability else []
    return {
        "kind": "executor",
        "id": executor.id,
        "user_id": executor.user_id,
        "name": executor.display_name,
        "org_type": executor.org_type,
        "lat": executor.latitude,
        "lng": executor.longitude,
        "region": executor.region.name_ru if executor.region else None,
        "rating_avg": float(executor.rating_avg) if executor.rating_avg is not None else None,
        "services": [s.name_ru for s in services],
        "is_complete": executor.is_complete,
        "has_design_engineer": executor.has_design_engineer,
        "detail_url": url_for("profile.executor_public_profile", user_id=executor.user_id),
    }


def _visible_constructors_query():
    return ConstructorProfile.query.join(User, ConstructorProfile.user_id == User.id).filter(
        User.role == "constructor",
        ConstructorProfile.latitude.isnot(None),
        ConstructorProfile.longitude.isnot(None),
        ConstructorProfile.display_name.isnot(None),
        ConstructorProfile.description.isnot(None),
        ConstructorProfile.region_id.isnot(None),
    )


def _constructor_payload(constructor):
    return {
        "kind": "constructor",
        "id": constructor.id,
        "user_id": constructor.user_id,
        "name": constructor.display_name,
        "lat": constructor.latitude,
        "lng": constructor.longitude,
        "region": constructor.region.name_ru if constructor.region else None,
        "experience_years": constructor.experience_years,
        "detail_url": url_for("constructors.detail", constructor_id=constructor.id),
    }


def _visible_sellers_query():
    """«Продавцы» на карте — активные объявления барахолки с указанной
    точкой (ставится через карту в форме объявления, необязательно)."""
    return Listing.query.filter(
        Listing.status == "active",
        Listing.latitude.isnot(None),
        Listing.longitude.isnot(None),
    )


def _seller_payload(listing):
    return {
        "kind": "seller",
        "id": listing.id,
        "user_id": listing.author_id,
        "name": listing.title,
        "lat": listing.latitude,
        "lng": listing.longitude,
        "region": listing.region.name_ru if listing.region else None,
        "price": float(listing.price) if listing.price is not None else None,
        "currency": listing.currency,
        "intent": listing.listing_intent,
        "detail_url": url_for("marketplace.detail", listing_id=listing.id),
    }


@bp.route("/map")
@paywall_required
def index():
    return render_template(
        "map/index.html",
        regions=Region.query.order_by(Region.name_ru).all(),
        service_categories=ServiceCategory.query.order_by(ServiceCategory.name_ru).all(),
        constructors_view=request.args.get("constructors") == "1",
    )


@bp.route("/map/executors.json")
@login_required
def executors_json():
    query = _visible_executors_query()

    org_type = request.args.get("org_type")
    if org_type in ("master", "tsekh", "zavod"):
        query = query.filter(ExecutorProfile.org_type == org_type)

    region_id = request.args.get("region_id", type=int)
    if region_id:
        query = query.filter(ExecutorProfile.region_id == region_id)

    min_rating = request.args.get("min_rating", type=float)
    if min_rating:
        query = query.filter(ExecutorProfile.rating_avg >= min_rating)

    if request.args.get("has_design_engineer") == "1":
        query = query.filter(ExecutorProfile.has_design_engineer.is_(True))

    service_category_id = request.args.get("service_category_id", type=int)
    executors = query.all()
    if service_category_id:
        executors = [
            e for e in executors
            if e.capability and any(s.id == service_category_id for s in e.capability.service_categories)
        ]

    return jsonify([_executor_payload(e) for e in executors if e.is_complete])


@bp.route("/map/constructors.json")
@login_required
def constructors_json():
    query = _visible_constructors_query()

    region_id = request.args.get("region_id", type=int)
    if region_id:
        query = query.filter(ConstructorProfile.region_id == region_id)

    return jsonify([_constructor_payload(c) for c in query.all() if c.is_complete])


@bp.route("/map/sellers.json")
@login_required
def sellers_json():
    query = _visible_sellers_query()

    region_id = request.args.get("region_id", type=int)
    if region_id:
        query = query.filter(Listing.region_id == region_id)

    intent = request.args.get("intent")
    if intent in ("sell", "buy"):
        query = query.filter(Listing.listing_intent == intent)

    return jsonify([_seller_payload(listing) for listing in query.all()])


_KIND_QUERIES = {
    "executor": (lambda: [e for e in _visible_executors_query().all() if e.is_complete], _executor_payload),
    "constructor": (lambda: [c for c in _visible_constructors_query().all() if c.is_complete], _constructor_payload),
    "seller": (lambda: _visible_sellers_query().all(), _seller_payload),
}


@bp.route("/map/nearby.json")
@login_required
def nearby_json():
    """Геопоиск «рядом»: сортировка по расстоянию от точки. kinds= — через
    запятую, какие типы точек искать (executor,constructor,seller);
    по умолчанию — только исполнители, как и раньше."""
    lat = request.args.get("lat", type=float)
    lng = request.args.get("lng", type=float)
    radius_km = request.args.get("radius_km", type=float, default=25)
    kinds = [k for k in (request.args.get("kinds") or "executor").split(",") if k in _KIND_QUERIES]

    if lat is None or lng is None:
        return jsonify({"error": "lat/lng обязательны"}), 400

    results = []
    for kind in kinds:
        fetch, payload_fn = _KIND_QUERIES[kind]
        for item in fetch():
            distance = haversine_km(lat, lng, item.latitude, item.longitude)
            if distance is not None and distance <= radius_km:
                payload = payload_fn(item)
                payload["distance_km"] = round(distance, 1)
                results.append(payload)

    results.sort(key=lambda item: item["distance_km"])
    return jsonify(results)
