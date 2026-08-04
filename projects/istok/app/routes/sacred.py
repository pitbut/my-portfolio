"""Раздел «Священные источники мира»."""
from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from sqlalchemy import func

from app import db
from app.models import EditSuggestion, SacredSource
from app.routes.reviews import reviews_for

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
