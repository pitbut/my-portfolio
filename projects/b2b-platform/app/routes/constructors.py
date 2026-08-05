"""Каталог конструкторов-фрилансеров — отдельная роль (не заказчик и не
исполнитель), к которой может обратиться любая из сторон, если у своего
предприятия нет штатного конструктора."""
from flask import Blueprint, abort, render_template, request

from app import db
from app.decorators import paywall_required
from app.models import ConstructorProfile, Region

bp = Blueprint("constructors", __name__, url_prefix="/constructors")


def _visible_query():
    return ConstructorProfile.query.filter(
        ConstructorProfile.display_name.isnot(None),
        ConstructorProfile.description.isnot(None),
        ConstructorProfile.region_id.isnot(None),
    )


@bp.route("")
@paywall_required
def index():
    query = _visible_query()

    region_id = request.args.get("region_id", type=int)
    if region_id:
        query = query.filter(ConstructorProfile.region_id == region_id)

    return render_template(
        "constructors/index.html",
        constructors=query.order_by(ConstructorProfile.display_name).all(),
        regions=Region.query.order_by(Region.name_ru).all(),
    )


@bp.route("/<int:constructor_id>")
@paywall_required
def detail(constructor_id):
    profile = db.session.get(ConstructorProfile, constructor_id)
    if profile is None or not profile.is_complete:
        abort(404)
    return render_template("constructors/detail.html", profile=profile)
