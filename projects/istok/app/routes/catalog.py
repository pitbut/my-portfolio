"""Раздел «Каталог цен на питьевую воду»."""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.models import Supplier, WaterBrand

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


@bp.route("/<slug>")
def detail(slug):
    brand = WaterBrand.query.filter_by(slug=slug).first()
    if brand is None:
        abort(404)
    suppliers = (
        Supplier.query.filter_by(water_brand_id=brand.id)
        .order_by(Supplier.verified.desc(), Supplier.name)
        .all()
    )
    return render_template("catalog/detail.html", brand=brand, suppliers=suppliers)


@bp.route("/<slug>/add-supplier", methods=["GET", "POST"])
@login_required
def add_supplier(slug):
    brand = WaterBrand.query.filter_by(slug=slug).first()
    if brand is None:
        abort(404)

    if not current_user.email_confirmed:
        flash("Сначала подтвердите email — так мы защищаем каталог от спама.", "error")
        return redirect(url_for("catalog.detail", slug=slug))

    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        supplier_type = (request.form.get("supplier_type") or "").strip()
        address = (request.form.get("address") or "").strip()
        phone = (request.form.get("phone") or "").strip()
        website = (request.form.get("website_url") or "").strip()
        latitude = request.form.get("latitude") or None
        longitude = request.form.get("longitude") or None

        if not name or not address:
            flash("Заполните название и адрес.", "error")
            return render_template("catalog/add_supplier.html", brand=brand)

        try:
            latitude = float(latitude) if latitude else None
            longitude = float(longitude) if longitude else None
        except ValueError:
            latitude = longitude = None

        supplier = Supplier(
            water_brand_id=brand.id,
            name=name,
            supplier_type=supplier_type or None,
            address=address,
            latitude=latitude,
            longitude=longitude,
            phone=phone or None,
            website=website or None,
            verified=False,
            added_by_user_id=current_user.id,
        )
        db.session.add(supplier)
        db.session.commit()

        flash(
            "Точка продажи добавлена и уже видна в каталоге с пометкой «не проверено» "
            "— администрация проверит её и подтвердит.",
            "success",
        )
        return redirect(url_for("catalog.detail", slug=slug))

    return render_template("catalog/add_supplier.html", brand=brand)
