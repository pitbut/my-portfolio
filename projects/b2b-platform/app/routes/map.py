"""Модуль 4 — интерактивная карта Узбекистана и гео-поиск исполнителей."""
from flask import Blueprint, jsonify, render_template, request, url_for
from flask_login import login_required

from app.decorators import paywall_required
from app.geo import haversine_km
from app.models import ConstructorProfile, ExecutorProfile, Listing, Region, ServiceCategory, User

bp = Blueprint("map", __name__)


def _effective_coords(entity):
    """Своя точка на карте необязательна везде (ставится по желанию через
    picker) — большинство профилей на практике заполняют только адрес/регион
    текстом и никогда не кликают по карте. Не показывать их на карте вовсе
    из-за этого неверно: раз регион выбран (а он обязателен для «полного»
    профиля/объявления), используем координаты центра региона как приближение,
    пока точная точка не указана."""
    if entity.latitude is not None and entity.longitude is not None:
        return entity.latitude, entity.longitude, False
    region = getattr(entity, "region", None)
    if region is not None and region.latitude is not None and region.longitude is not None:
        return region.latitude, region.longitude, True
    return None, None, False


def _visible_executors_query():
    """Профиль виден на карте/в геопоиске только когда действительно
    заполнен (оборудование, техвозможности, регион) — иначе показывать
    нечего и незачем. Плюс User.role == 'executor': если пользователь
    переключился на другую роль в настройках, его старая анкета исполнителя
    остаётся в базе, но с карты пропадает. Точные координаты необязательны —
    см. _effective_coords()."""
    return ExecutorProfile.query.join(User, ExecutorProfile.user_id == User.id).filter(
        User.role == "executor",
        ExecutorProfile.region_id.isnot(None),
        ExecutorProfile.display_name.isnot(None),
    )


def _executor_payload(executor):
    services = executor.capability.service_categories if executor.capability else []
    lat, lng, approximate = _effective_coords(executor)
    return {
        "kind": "executor",
        "id": executor.id,
        "user_id": executor.user_id,
        "name": executor.display_name,
        "org_type": executor.org_type,
        "lat": lat,
        "lng": lng,
        "approximate": approximate,
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
        ConstructorProfile.display_name.isnot(None),
        ConstructorProfile.description.isnot(None),
        ConstructorProfile.region_id.isnot(None),
    )


def _constructor_payload(constructor):
    lat, lng, approximate = _effective_coords(constructor)
    return {
        "kind": "constructor",
        "id": constructor.id,
        "user_id": constructor.user_id,
        "name": constructor.display_name,
        "lat": lat,
        "lng": lng,
        "approximate": approximate,
        "region": constructor.region.name_ru if constructor.region else None,
        "experience_years": constructor.experience_years,
        "detail_url": url_for("constructors.detail", constructor_id=constructor.id),
    }


def _visible_sellers_query():
    """«Продавцы» на карте — активные объявления барахолки. Регион у
    объявления обязателен, точная точка — нет, см. _effective_coords()."""
    return Listing.query.filter(Listing.status == "active")


def _seller_payload(listing):
    lat, lng, approximate = _effective_coords(listing)
    return {
        "kind": "seller",
        "id": listing.id,
        "user_id": listing.author_id,
        "name": listing.title,
        "lat": lat,
        "lng": lng,
        "approximate": approximate,
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

    payloads = [_executor_payload(e) for e in executors if e.is_complete]
    return jsonify([p for p in payloads if p["lat"] is not None])


@bp.route("/map/constructors.json")
@login_required
def constructors_json():
    query = _visible_constructors_query()

    region_id = request.args.get("region_id", type=int)
    if region_id:
        query = query.filter(ConstructorProfile.region_id == region_id)

    payloads = [_constructor_payload(c) for c in query.all() if c.is_complete]
    return jsonify([p for p in payloads if p["lat"] is not None])


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

    payloads = [_seller_payload(listing) for listing in query.all()]
    return jsonify([p for p in payloads if p["lat"] is not None])


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
            item_lat, item_lng, _ = _effective_coords(item)
            if item_lat is None:
                continue
            distance = haversine_km(lat, lng, item_lat, item_lng)
            if distance is not None and distance <= radius_km:
                payload = payload_fn(item)
                payload["distance_km"] = round(distance, 1)
                results.append(payload)

    results.sort(key=lambda item: item["distance_km"])
    return jsonify(results)
