"""Раздел «Священные источники мира»."""
from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from app import db
from app.models import EditSuggestion, SacredSource
from app.photos import upload_photo
from app.routes.reviews import reviews_for
from app.slugify import unique_slug

bp = Blueprint("sacred", __name__, template_folder="../templates/sacred")

MAX_SUGGESTION_LENGTH = 4000


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


@bp.route("/add", methods=["GET", "POST"])
@login_required
def add():
    if not current_user.email_confirmed:
        flash("Сначала подтвердите email — так мы защищаем каталог от спама.", "error")
        return redirect(url_for("sacred.index"))

    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        country = (request.form.get("country") or "").strip()
        location = (request.form.get("location") or "").strip()
        belief = (request.form.get("belief") or "").strip()
        allowed = (request.form.get("allowed") or "").strip()
        forbidden = (request.form.get("forbidden") or "").strip()
        description = (request.form.get("description") or "").strip()

        if not name or not country or not location or not belief or not allowed or not forbidden:
            flash("Заполните название, страну, местоположение и разделы «во что верят»/«что можно»/«что нельзя».", "error")
            return render_template("sacred/add.html")

        image_url, photo_error = upload_photo(request.files.get("photo"))
        if photo_error:
            flash(photo_error, "info")

        used_slugs = {row[0] for row in db.session.query(SacredSource.slug).all()}
        source = SacredSource(
            slug=unique_slug(name, used_slugs, "source"),
            name=name,
            country=country,
            location=location,
            belief=belief,
            allowed=allowed,
            forbidden=forbidden,
            description=description or None,
            image_url=image_url,
            verified=False,
            added_by_user_id=current_user.id,
        )
        db.session.add(source)
        db.session.commit()

        flash(
            "Источник добавлен и уже виден на сайте с пометкой «не проверено» "
            "— администрация проверит и подтвердит.",
            "success",
        )
        return redirect(url_for("sacred.detail", slug=source.slug))

    return render_template("sacred/add.html")


@bp.route("/<slug>")
def detail(slug):
    source = SacredSource.query.filter_by(slug=slug).first()
    if source is None:
        abort(404)
    reviews, avg_rating = reviews_for("sacred_source", source.id)
    return render_template(
        "sacred/detail.html",
        source=source,
        reviews=reviews,
        avg_rating=avg_rating,
        target_type="sacred_source",
        target_id=source.id,
    )


@bp.route("/<slug>/suggest", methods=["POST"])
def suggest(slug):
    source = SacredSource.query.filter_by(slug=slug).first()
    if source is None:
        abort(404)

    # honeypot: скрытое от людей поле формы — если его заполнил бот,
    # тихо делаем вид, что всё отправилось, но ничего не сохраняем.
    if request.form.get("website"):
        flash("Спасибо! Предложение отправлено на модерацию.", "success")
        return redirect(url_for("sacred.detail", slug=slug))

    field_name = request.form.get("field_name", "")
    proposed_value = (request.form.get("proposed_value") or "").strip()
    message = (request.form.get("message") or "").strip()
    submitter_name = (request.form.get("submitter_name") or "").strip()

    if field_name not in EditSuggestion.FIELD_LABELS:
        flash("Не удалось определить поле для правки.", "error")
        return redirect(url_for("sacred.detail", slug=slug))

    if field_name == "image_url":
        # для фото — либо загруженный файл (приоритет), либо вручную
        # вставленная ссылка в том же текстовом поле.
        uploaded_url, photo_error = upload_photo(request.files.get("photo"))
        if uploaded_url:
            proposed_value = uploaded_url
        elif photo_error and not proposed_value:
            flash(photo_error, "error")
            return redirect(url_for("sacred.detail", slug=slug))
        elif photo_error:
            flash(photo_error, "info")

    if not proposed_value:
        flash("Опишите, что предлагаете изменить.", "error")
        return redirect(url_for("sacred.detail", slug=slug))

    if len(proposed_value) > MAX_SUGGESTION_LENGTH or len(message) > MAX_SUGGESTION_LENGTH:
        flash("Текст слишком длинный.", "error")
        return redirect(url_for("sacred.detail", slug=slug))

    suggestion = EditSuggestion(
        source_id=source.id,
        field_name=field_name,
        proposed_value=proposed_value,
        message=message or None,
        submitter_name=submitter_name or None,
    )
    db.session.add(suggestion)
    db.session.commit()

    flash("Спасибо! Предложение отправлено на модерацию.", "success")
    return redirect(url_for("sacred.detail", slug=slug))
