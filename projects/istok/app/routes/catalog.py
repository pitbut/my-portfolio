"""Раздел «Каталог цен на питьевую воду»."""
from flask import Blueprint, render_template, request

from app.models import WaterBrand

bp = Blueprint("catalog", __name__)

SORT_OPTIONS = {
    "price_asc": (WaterBrand.price_rub.asc(), "цена: по возрастанию"),
    "price_desc": (WaterBrand.price_rub.desc(), "цена: по убыванию"),
    "name": (WaterBrand.name.asc(), "по названию"),
    "mineralization": (WaterBrand.mineralization_mg_l.asc(), "по минерализации"),
}
DEFAULT_SORT = "price_asc"


@bp.route("/")
def index():
    sort = request.args.get("sort", DEFAULT_SORT)
    if sort not in SORT_OPTIONS:
        sort = DEFAULT_SORT
    order_by, _ = SORT_OPTIONS[sort]

    brands = WaterBrand.query.order_by(order_by).all()

    return render_template(
        "catalog/index.html",
        brands=brands,
        sort=sort,
        sort_options=SORT_OPTIONS,
    )
