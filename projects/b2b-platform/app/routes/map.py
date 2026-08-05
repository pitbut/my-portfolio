"""Модуль 4 — интерактивная карта Узбекистана и гео-поиск исполнителей."""
from flask import Blueprint, jsonify, render_template, request
from flask_login import login_required

from app.decorators import paywall_required
from app.geo import haversine_km
from app.models import ExecutorProfile, Region, ServiceCategory

bp = Blueprint("map", __name__)


def _visible_executors_query():
    """Профиль виден на карте/в геопоиске только когда действительно
    заполнен (есть координаты, оборудование, техвозможности) — иначе
    показывать нечего и незачем."""
    return ExecutorProfile.query.filter(
        ExecutorProfile.latitude.isnot(None),
        ExecutorProfile.longitude.isnot(None),
        ExecutorProfile.display_name.isnot(None),
    )


def _executor_payload(executor):
    services = executor.capability.service_categories if executor.capability else []
    return {
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
    }


@bp.route("/map")
@paywall_required
def index():
    return render_template(
        "map/index.html",
        regions=Region.query.order_by(Region.name_ru).all(),
        service_categories=ServiceCategory.query.order_by(ServiceCategory.name_ru).all(),
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


@bp.route("/map/nearby.json")
@login_required
def nearby_json():
    """Геопоиск «рядом»: сортировка исполнителей по расстоянию от точки."""
    lat = request.args.get("lat", type=float)
    lng = request.args.get("lng", type=float)
    radius_km = request.args.get("radius_km", type=float, default=25)

    if lat is None or lng is None:
        return jsonify({"error": "lat/lng обязательны"}), 400

    results = []
    for executor in _visible_executors_query().all():
        if not executor.is_complete:
            continue
        distance = haversine_km(lat, lng, executor.latitude, executor.longitude)
        if distance is not None and distance <= radius_km:
            payload = _executor_payload(executor)
            payload["distance_km"] = round(distance, 1)
            results.append(payload)

    results.sort(key=lambda item: item["distance_km"])
    return jsonify(results)
