"""Раздел «Каталог цен на питьевую воду»."""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from app import db
from app.models import Review, Supplier, WaterBrand
from app.photos import upload_photo
from app.routes.reviews import reviews_for

bp = Blueprint("catalog", __name__)

# Цена хранится в собственной валюте каждой марки (см. WaterBrand.currency),
# поэтому сортировка по цене сравнивает "сырые" числа разных валют — это
# осознанный компромисс, а не пересчёт по курсу.
SORT_OPTIONS = {
    "price_asc": (WaterBrand.price.asc(), "цена: по возрастанию"),
    "price_desc": (WaterBrand.price.desc(), "цена: по убыванию"),
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

    country = (request.args.get("country") or "").strip()

    query = WaterBrand.query
    if country:
        query = query.filter_by(country=country)
    brands = query.order_by(order_by).all()

    countries = [
        row[0]
        for row in db.session.query(WaterBrand.country)
        .filter(WaterBrand.country.isnot(None))
        .distinct()
        .order_by(WaterBrand.country)
        .all()
    ]

    avg_ratings = dict(
        db.session.query(Review.target_id, func.avg(Review.rating))
        .filter(Review.target_type == "water_brand")
        .group_by(Review.target_id)
        .all()
    )

    return render_template(
        "catalog/index.html",
        brands=brands,
        sort=sort,
        sort_options=SORT_OPTIONS,
        countries=countries,
        selected_country=country,
        avg_ratings=avg_ratings,
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
    reviews, avg_rating = reviews_for("water_brand", brand.id)
    return render_template(
        "catalog/detail.html",
        brand=brand,
        suppliers=suppliers,
        reviews=reviews,
        avg_rating=avg_rating,
        target_type="water_brand",
        target_id=brand.id,
    )


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

        image_url, photo_error = upload_photo(request.files.get("photo"))
        if photo_error:
            flash(photo_error, "info")

        supplier = Supplier(
            water_brand_id=brand.id,
            name=name,
            supplier_type=supplier_type or None,
            address=address,
            latitude=latitude,
            longitude=longitude,
            phone=phone or None,
            website=website or None,
            image_url=image_url,
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
