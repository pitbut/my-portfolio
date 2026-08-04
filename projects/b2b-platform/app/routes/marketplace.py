"""Модуль 8 — барахолка: купля-продажа станков и инструмента."""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user

from app import db
from app.decorators import paywall_required
from app.models import Listing, ListingCategory, ListingMedia, ListingResponse, Region
from app.notify import notify
from app.photos import upload_photo

bp = Blueprint("marketplace", __name__, url_prefix="/marketplace")


def _to_int(value):
    value = (value or "").strip()
    return int(value) if value.lstrip("-").isdigit() else None


def _to_decimal(value):
    value = (value or "").strip()
    try:
        return float(value) if value else None
    except ValueError:
        return None


@bp.route("")
@paywall_required
def index():
    query = Listing.query.filter_by(status="active")

    category_id = request.args.get("category_id", type=int)
    if category_id:
        query = query.filter_by(category_id=category_id)
    intent = request.args.get("intent")
    if intent in ("sell", "buy"):
        query = query.filter_by(listing_intent=intent)
    region_id = request.args.get("region_id", type=int)
    if region_id:
        query = query.filter_by(region_id=region_id)

    listings = query.order_by(Listing.created_at.desc()).all()
    return render_template(
        "marketplace/index.html", listings=listings,
        categories=ListingCategory.query.order_by(ListingCategory.name_ru).all(),
        regions=Region.query.order_by(Region.name_ru).all(),
    )


@bp.route("/new", methods=["GET", "POST"])
@paywall_required
def new_listing():
    categories = ListingCategory.query.order_by(ListingCategory.name_ru).all()
    regions = Region.query.order_by(Region.name_ru).all()

    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        description = (request.form.get("description") or "").strip()
        listing_intent = request.form.get("listing_intent")
        category_id = _to_int(request.form.get("category_id"))
        region_id = _to_int(request.form.get("region_id"))

        errors = []
        if not title:
            errors.append("Укажите название.")
        if not description:
            errors.append("Добавьте описание.")
        if listing_intent not in ("sell", "buy"):
            errors.append("Выберите: продаю или ищу купить.")
        if not category_id:
            errors.append("Выберите категорию.")
        if not region_id:
            errors.append("Выберите регион.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("marketplace/new.html", categories=categories, regions=regions, form=request.form)

        listing = Listing(
            author_id=current_user.id, listing_intent=listing_intent, category_id=category_id,
            title=title, description=description, content_language=current_user.preferred_language,
            condition=request.form.get("condition") if listing_intent == "sell" else None,
            price=_to_decimal(request.form.get("price")),
            currency=request.form.get("currency") or "UZS",
            price_negotiable=request.form.get("price_negotiable") == "1",
            region_id=region_id, city_id=_to_int(request.form.get("city_id")),
            latitude=_to_decimal(request.form.get("latitude")), longitude=_to_decimal(request.form.get("longitude")),
        )
        db.session.add(listing)
        db.session.flush()

        sort_order = 0
        for photo in request.files.getlist("photos")[:8]:
            url, error = upload_photo(photo)
            if url:
                db.session.add(ListingMedia(listing_id=listing.id, media_type="photo", file_url=url, sort_order=sort_order))
                sort_order += 1
            elif error:
                flash(error, "info")

        db.session.commit()
        flash("Объявление опубликовано.", "success")
        return redirect(url_for("marketplace.detail", listing_id=listing.id))

    return render_template("marketplace/new.html", categories=categories, regions=regions, form={})


@bp.route("/<int:listing_id>")
@paywall_required
def detail(listing_id):
    listing = db.session.get(Listing, listing_id)
    if listing is None:
        abort(404)
    is_owner = listing.author_id == current_user.id
    return render_template("marketplace/detail.html", listing=listing, is_owner=is_owner)


@bp.route("/<int:listing_id>/respond", methods=["POST"])
@paywall_required
def respond(listing_id):
    listing = db.session.get(Listing, listing_id)
    if listing is None:
        abort(404)
    if listing.author_id == current_user.id:
        flash("Нельзя откликнуться на собственное объявление.", "error")
        return redirect(url_for("marketplace.detail", listing_id=listing.id))
    if listing.status != "active":
        flash("Объявление больше не активно.", "error")
        return redirect(url_for("marketplace.detail", listing_id=listing.id))

    message = (request.form.get("message") or "").strip() or None
    offered_price = _to_decimal(request.form.get("offered_price"))
    db.session.add(ListingResponse(listing_id=listing.id, from_user_id=current_user.id, message=message, offered_price=offered_price))
    db.session.commit()

    notify(
        listing.author, "listing_response", title=f"Отклик на объявление «{listing.title}»",
        body=message or (f"Предложена цена: {offered_price}" if offered_price else "Кто-то заинтересовался объявлением"),
        url=url_for("marketplace.detail", listing_id=listing.id),
    )
    flash("Отклик отправлен, автор объявления уведомлён.", "success")
    return redirect(url_for("marketplace.detail", listing_id=listing.id))


@bp.route("/<int:listing_id>/status", methods=["POST"])
@paywall_required
def set_status(listing_id):
    listing = db.session.get(Listing, listing_id)
    if listing is None or listing.author_id != current_user.id:
        abort(404)
    new_status = request.form.get("status")
    if new_status in ("active", "reserved", "closed"):
        listing.status = new_status
        db.session.commit()
        flash("Статус объявления обновлён.", "success")
    return redirect(url_for("marketplace.detail", listing_id=listing.id))
