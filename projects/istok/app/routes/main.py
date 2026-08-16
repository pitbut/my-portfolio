"""Главная страница и разделы без собственного блюпринта (оборудование,
опыты, доставка, контакты)."""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func, or_

from app import db
from app.models import (
    Article,
    Book,
    ContactMessage,
    DeliveryService,
    Equipment,
    Experiment,
    SacredSource,
    WaterBrand,
)
from app.photos import upload_photo
from app.routes.reviews import reviews_for
from app.slugify import unique_slug

bp = Blueprint("main", __name__)

MAX_MESSAGE_LENGTH = 4000

# Реестр разделов для site-wide поиска (/search): по каким полям искать,
# как назвать раздел в результатах и куда вести ссылку карточки.
SEARCH_SPECS = [
    ("sacred_source", "Священные источники", "sacred.detail", SacredSource, "name",
     lambda m: [m.name, m.location, m.belief]),
    ("water_brand", "Марки воды", "catalog.detail", WaterBrand, "name",
     lambda m: [m.name, m.origin, m.description]),
    ("book", "Библиотека", "library.detail", Book, "title",
     lambda m: [m.title, m.author, m.description]),
    ("article", "Статьи", "articles.detail", Article, "title",
     lambda m: [m.title, m.body, m.summary]),
    ("equipment", "Оборудование", "main.equipment_detail", Equipment, "name",
     lambda m: [m.name, m.description, m.manufacturer]),
    ("experiment", "Опыты", "main.experiment_detail", Experiment, "title",
     lambda m: [m.title, m.description]),
    ("delivery_service", "Доставка воды", "main.delivery_detail", DeliveryService, "name",
     lambda m: [m.name, m.coverage]),
]


@bp.route("/")
def index():
    sacred_sources = SacredSource.query.order_by(SacredSource.name).limit(3).all()
    articles = Article.query.order_by(Article.published_at.desc()).limit(3).all()
    water_brands = WaterBrand.query.order_by(WaterBrand.price).limit(4).all()
    books = Book.query.order_by(Book.created_at.desc()).limit(3).all()
    equipment = Equipment.query.order_by(Equipment.created_at.desc()).limit(3).all()
    experiments = Experiment.query.order_by(Experiment.created_at.desc()).limit(3).all()
    delivery_services = DeliveryService.query.order_by(DeliveryService.name).limit(3).all()

    return render_template(
        "main/index.html",
        sacred_sources=sacred_sources,
        articles=articles,
        water_brands=water_brands,
        books=books,
        equipment=equipment,
        experiments=experiments,
        delivery_services=delivery_services,
    )


@bp.route("/equipment")
def equipment_list():
    category = request.args.get("category")
    q = (request.args.get("q") or "").strip()

    query = Equipment.query
    if category:
        query = query.filter_by(category=category)
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                Equipment.name.ilike(like),
                Equipment.description.ilike(like),
                Equipment.manufacturer.ilike(like),
            )
        )
    equipment = query.order_by(Equipment.category, Equipment.name).all()

    category_counts = (
        db.session.query(Equipment.category, func.count(Equipment.id))
        .group_by(Equipment.category)
        .order_by(Equipment.category)
        .all()
    )

    return render_template(
        "main/equipment.html",
        equipment=equipment,
        active_category=category,
        q=q,
        category_counts=category_counts,
    )


@bp.route("/equipment/add", methods=["GET", "POST"])
@login_required
def equipment_add():
    if not current_user.email_confirmed:
        flash("Сначала подтвердите email — так мы защищаем каталог от спама.", "error")
        return redirect(url_for("main.equipment_list"))

    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        category = (request.form.get("category") or "").strip()
        description = (request.form.get("description") or "").strip()
        manufacturer = (request.form.get("manufacturer") or "").strip()
        price_rub = request.form.get("price_rub") or None

        if not name or not category or not description:
            flash("Заполните название, категорию и описание.", "error")
            return render_template("main/equipment_add.html")

        try:
            price_rub = float(price_rub) if price_rub else None
        except ValueError:
            price_rub = None

        image_url, photo_error = upload_photo(request.files.get("photo"))
        if photo_error:
            flash(photo_error, "info")

        used_slugs = {row[0] for row in db.session.query(Equipment.slug).all()}
        item = Equipment(
            slug=unique_slug(name, used_slugs, "equipment"),
            category=category,
            name=name,
            description=description,
            price_rub=price_rub,
            manufacturer=manufacturer or None,
            image_url=image_url,
            verified=False,
            added_by_user_id=current_user.id,
        )
        db.session.add(item)
        db.session.commit()

        flash(
            "Оборудование добавлено и уже видно в каталоге с пометкой «не проверено» "
            "— администрация проверит и подтвердит.",
            "success",
        )
        return redirect(url_for("main.equipment_detail", slug=item.slug))

    return render_template("main/equipment_add.html")


@bp.route("/equipment/<slug>")
def equipment_detail(slug):
    item = Equipment.query.filter_by(slug=slug).first()
    if item is None:
        abort(404)
    reviews, avg_rating = reviews_for("equipment", item.id)
    return render_template(
        "main/equipment_detail.html",
        item=item,
        reviews=reviews,
        avg_rating=avg_rating,
        target_type="equipment",
        target_id=item.id,
    )


@bp.route("/experiments")
def experiments_list():
    experiments = Experiment.query.order_by(Experiment.title).all()
    return render_template("main/experiments.html", experiments=experiments)


@bp.route("/experiments/add", methods=["GET", "POST"])
@login_required
def experiment_add():
    if not current_user.email_confirmed:
        flash("Сначала подтвердите email — так мы защищаем каталог от спама.", "error")
        return redirect(url_for("main.experiments_list"))

    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        description = (request.form.get("description") or "").strip()
        verdict = (request.form.get("verdict") or "").strip()

        if not title or not description or verdict not in ("наука", "миф"):
            flash("Заполните название, описание и выберите вердикт.", "error")
            return render_template("main/experiment_add.html")

        used_slugs = {row[0] for row in db.session.query(Experiment.slug).all()}
        experiment = Experiment(
            slug=unique_slug(title, used_slugs, "experiment"),
            title=title,
            description=description,
            verdict=verdict,
            verified=False,
            added_by_user_id=current_user.id,
        )
        db.session.add(experiment)
        db.session.commit()

        flash(
            "Опыт добавлен и уже виден на сайте с пометкой «не проверено» "
            "— администрация проверит и подтвердит.",
            "success",
        )
        return redirect(url_for("main.experiment_detail", slug=experiment.slug))

    return render_template("main/experiment_add.html")


@bp.route("/experiments/<slug>")
def experiment_detail(slug):
    experiment = Experiment.query.filter_by(slug=slug).first()
    if experiment is None:
        abort(404)
    reviews, avg_rating = reviews_for("experiment", experiment.id)
    return render_template(
        "main/experiment_detail.html",
        experiment=experiment,
        reviews=reviews,
        avg_rating=avg_rating,
        target_type="experiment",
        target_id=experiment.id,
    )


@bp.route("/delivery")
def delivery_list():
    services = DeliveryService.query.order_by(DeliveryService.name).all()
    return render_template("main/delivery.html", services=services)


@bp.route("/delivery/add", methods=["GET", "POST"])
@login_required
def delivery_add():
    if not current_user.email_confirmed:
        flash("Сначала подтвердите email — так мы защищаем каталог от спама.", "error")
        return redirect(url_for("main.delivery_list"))

    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        coverage = (request.form.get("coverage") or "").strip()
        delivery_time = (request.form.get("delivery_time") or "").strip()
        price_rub = request.form.get("price_rub") or None
        phone = (request.form.get("phone") or "").strip()
        website = (request.form.get("website") or "").strip()

        if not name or not delivery_time:
            flash("Заполните название и сроки доставки.", "error")
            return render_template("main/delivery_add.html")

        try:
            price_rub = float(price_rub) if price_rub else None
        except ValueError:
            price_rub = None

        used_slugs = {row[0] for row in db.session.query(DeliveryService.slug).all()}
        service = DeliveryService(
            slug=unique_slug(name, used_slugs, "service"),
            name=name,
            coverage=coverage or None,
            delivery_time=delivery_time,
            price_rub=price_rub,
            phone=phone or None,
            website=website or None,
            verified=False,
            added_by_user_id=current_user.id,
        )
        db.session.add(service)
        db.session.commit()

        flash(
            "Служба доставки добавлена и уже видна на сайте с пометкой «не проверено» "
            "— администрация проверит и подтвердит.",
            "success",
        )
        return redirect(url_for("main.delivery_detail", slug=service.slug))

    return render_template("main/delivery_add.html")


@bp.route("/delivery/<slug>")
def delivery_detail(slug):
    service = DeliveryService.query.filter_by(slug=slug).first()
    if service is None:
        abort(404)
    reviews, avg_rating = reviews_for("delivery_service", service.id)
    return render_template(
        "main/delivery_detail.html",
        service=service,
        reviews=reviews,
        avg_rating=avg_rating,
        target_type="delivery_service",
        target_id=service.id,
    )


@bp.route("/search")
def search():
    q = (request.args.get("q") or "").strip()
    groups = []
    total = 0

    if q:
        like = f"%{q}%"
        for content_type, label, endpoint, model, name_field, fields_fn in SEARCH_SPECS:
            conditions = [f.ilike(like) for f in fields_fn(model) if f is not None]
            items = model.query.filter(or_(*conditions)).limit(20).all()
            if items:
                groups.append({
                    "type": content_type,
                    "label": label,
                    "results": [
                        {
                            "name": getattr(item, name_field),
                            "url": url_for(endpoint, slug=item.slug),
                            "verified": getattr(item, "verified", True),
                        }
                        for item in items
                    ],
                })
                total += len(items)

    return render_template("search.html", q=q, groups=groups, total=total)


@bp.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        # honeypot: скрытое поле, боты его заполняют, люди — нет
        if request.form.get("website"):
            flash("Спасибо! Сообщение отправлено.", "success")
            return redirect(url_for("main.contact"))

        name = (request.form.get("name") or "").strip()
        email = (request.form.get("email") or "").strip()
        message = (request.form.get("message") or "").strip()

        if not message:
            flash("Напишите текст сообщения.", "error")
            return redirect(url_for("main.contact"))
        if len(message) > MAX_MESSAGE_LENGTH:
            flash("Сообщение слишком длинное.", "error")
            return redirect(url_for("main.contact"))

        db.session.add(ContactMessage(name=name or None, email=email or None, message=message))
        db.session.commit()

        flash("Спасибо! Сообщение отправлено.", "success")
        return redirect(url_for("main.contact"))

    return render_template("main/contact.html")
