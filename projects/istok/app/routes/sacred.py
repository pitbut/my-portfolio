"""Раздел «Священные источники мира»."""
from flask import Blueprint, abort, current_app, render_template, request
from sqlalchemy import func

from app import db
from app.models import SacredSource

bp = Blueprint("sacred", __name__, template_folder="../templates/sacred")


@bp.route("/")
def index():
    country = request.args.get("country")
    page = request.args.get("page", 1, type=int)
    per_page = current_app.config["ITEMS_PER_PAGE"]

    query = SacredSource.query
    if country:
        query = query.filter_by(country=country)

    pagination = query.order_by(SacredSource.name).paginate(
        page=page, per_page=per_page, error_out=False
    )

    country_counts = (
        db.session.query(SacredSource.country, func.count(SacredSource.id))
        .group_by(SacredSource.country)
        .order_by(SacredSource.country)
        .all()
    )
    total_count = SacredSource.query.count()

    return render_template(
        "sacred/index.html",
        pagination=pagination,
        sources=pagination.items,
        country_counts=country_counts,
        active_country=country,
        total_count=total_count,
    )


@bp.route("/<slug>")
def detail(slug):
    source = SacredSource.query.filter_by(slug=slug).first()
    if source is None:
        abort(404)
    return render_template("sacred/detail.html", source=source)
