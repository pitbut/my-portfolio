"""Раздел «Каталог цен на питьевую воду»."""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func, or_

from app import db
from app.models import Review, Supplier, WaterBrand
from app.photos import upload_photo
from app.routes.reviews import reviews_for
from app.slugify import unique_slug

bp = Blueprint("catalog", __name__)

# Столбцы таблицы каталога, по которым можно кликнуть в заголовке и
# отсортировать (по возрастанию/убыванию, повторный клик по тому же
# столбцу переключает направление). "rating" — особый случай: считается
# в Python по уже посчитанным avg_ratings, а не в SQL, т.к. это агрегат
# из отдельной таблицы отзывов.
SORTABLE_COLUMNS = {
    "name": WaterBrand.name,
    "water_type": WaterBrand.water_type,
    "mineralization": WaterBrand.mineralization_mg_l,
    "volume": WaterBrand.volume_l,
    # Цена хранится в собственной валюте каждой марки (см. WaterBrand.currency),
    # поэтому сортировка по цене сравнивает "сырые" числа разных валют — это
    # осознанный компромисс, а не пересчёт по курсу.
    "price": WaterBrand.price,
    "country": WaterBrand.country,
}
DEFAULT_SORT_COLUMN = "price"
DEFAULT_SORT_DIR = "asc"


@bp.route("/")
def index():
    sort_column = request.args.get("sort", DEFAULT_SORT_COLUMN)
    if sort_column not in SORTABLE_COLUMNS and sort_column != "rating":
        sort_column = DEFAULT_SORT_COLUMN
    sort_dir = request.args.get("dir", DEFAULT_SORT_DIR)
    if sort_dir not in ("asc", "desc"):
        sort_dir = DEFAULT_SORT_DIR

    country = (request.args.get("country") or "").strip()

    query = WaterBrand.query
    if country:
        query = query.filter_by(country=country)

    avg_ratings = dict(
        db.session.query(Review.target_id, func.avg(Review.rating))
        .filter(Review.target_type == "water_brand")
        .group_by(Review.target_id)
        .all()
    )

    if sort_column == "rating":
        brands = query.all()
        brands.sort(key=lambda b: float(avg_ratings.get(b.id, -1)), reverse=(sort_dir == "desc"))
    else:
        column = SORTABLE_COLUMNS[sort_column]
        order_by = column.desc() if sort_dir == "desc" else column.asc()
        brands = query.order_by(order_by).all()

    countries = [
        row[0]
        for row in db.session.query(WaterBrand.country)
        .filter(WaterBrand.country.isnot(None))
        .distinct()
        .order_by(WaterBrand.country)
        .all()
    ]

    return render_template(
        "catalog/index.html",
        brands=brands,
        sort_column=sort_column,
        sort_dir=sort_dir,
        countries=countries,
        selected_country=country,
        avg_ratings=avg_ratings,
    )


@bp.route("/add", methods=["GET", "POST"])
@login_required
def add():
    if not current_user.email_confirmed:
        flash("Сначала подтвердите email — так мы защищаем каталог от спама.", "error")
        return redirect(url_for("catalog.index"))

    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        water_type = (request.form.get("water_type") or "").strip()
        volume_l = request.form.get("volume_l") or None
        price = request.form.get("price") or None
        currency = (request.form.get("currency") or "RUB").strip().upper()
        country = (request.form.get("country") or "").strip()
        origin = (request.form.get("origin") or "").strip()
        mineralization_mg_l = request.form.get("mineralization_mg_l") or None
        description = (request.form.get("description") or "").strip()

        if not name or not water_type or not volume_l or not price:
            flash("Заполните название, тип, объём и цену.", "error")
            return render_template("catalog/add.html", currencies=WaterBrand.CURRENCY_SYMBOLS)

        try:
            volume_l = float(volume_l)
            price = float(price)
        except ValueError:
            flash("Объём и цена должны быть числами.", "error")
            return render_template("catalog/add.html", currencies=WaterBrand.CURRENCY_SYMBOLS)

        try:
            mineralization_mg_l = int(mineralization_mg_l) if mineralization_mg_l else None
        except ValueError:
            mineralization_mg_l = None

        if currency not in WaterBrand.CURRENCY_SYMBOLS:
            currency = "RUB"

        used_slugs = {row[0] for row in db.session.query(WaterBrand.slug).all()}
        brand = WaterBrand(
            slug=unique_slug(name, used_slugs, "brand"),
            name=name,
            water_type=water_type,
            mineralization_mg_l=mineralization_mg_l,
            volume_l=volume_l,
            price=price,
            currency=currency,
            country=country or None,
            origin=origin or None,
            description=description or None,
            verified=False,
            added_by_user_id=current_user.id,
        )
        db.session.add(brand)
        db.session.commit()

        flash(
            "Марка добавлена и уже видна в каталоге с пометкой «не проверено» "
            "— администрация проверит сведения и подтвердит их.",
            "success",
        )
        return redirect(url_for("catalog.detail", slug=brand.slug))

    return render_template("catalog/add.html", currencies=WaterBrand.CURRENCY_SYMBOLS)


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


@bp.route("/suppliers")
def suppliers_map():
    """Все точки продажи сразу, на одной карте/списке — с поиском по
    названию и фильтрами по типу и объёму воды (в отличие от
    catalog.detail, где точки видны только в рамках одной марки)."""
    q = (request.args.get("q") or "").strip()
    water_type = (request.args.get("water_type") or "").strip()
    volume = request.args.get("volume", type=float)
    country = (request.args.get("country") or "").strip()

    query = Supplier.query.join(WaterBrand, Supplier.water_brand_id == WaterBrand.id)

    if q:
        like = f"%{q}%"
        query = query.filter(or_(Supplier.name.ilike(like), WaterBrand.name.ilike(like)))
    if water_type:
        query = query.filter(WaterBrand.water_type == water_type)
    if volume:
        query = query.filter(WaterBrand.volume_l == volume)
    if country:
        query = query.filter(WaterBrand.country == country)

    suppliers = query.order_by(Supplier.verified.desc(), Supplier.name).all()

    water_types = [
        row[0] for row in db.session.query(WaterBrand.water_type).distinct().order_by(WaterBrand.water_type).all()
    ]
    volumes = [
        row[0] for row in db.session.query(WaterBrand.volume_l).distinct().order_by(WaterBrand.volume_l).all()
    ]
    countries = [
        row[0]
        for row in db.session.query(WaterBrand.country)
        .filter(WaterBrand.country.isnot(None))
        .distinct()
        .order_by(WaterBrand.country)
        .all()
    ]

    return render_template(
        "catalog/suppliers.html",
        suppliers=suppliers,
        water_types=water_types,
        volumes=volumes,
        countries=countries,
        q=q,
        selected_water_type=water_type,
        selected_volume=volume,
        selected_country=country,
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
