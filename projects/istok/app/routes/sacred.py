"""Раздел «Священные источники мира»."""
from flask import Blueprint, abort, current_app, render_template, request

from app.models import SacredSource

bp = Blueprint("sacred", __name__, template_folder="../templates/sacred")


@bp.route("/")
def index():
    page = request.args.get("page", 1, type=int)
    per_page = current_app.config["ITEMS_PER_PAGE"]
    pagination = SacredSource.query.order_by(SacredSource.name).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return render_template("sacred/index.html", pagination=pagination, sources=pagination.items)


@bp.route("/<slug>")
def detail(slug):
    source = SacredSource.query.filter_by(slug=slug).first()
    if source is None:
        abort(404)
    return render_template("sacred/detail.html", source=source)
