"""Отзывы с оценкой на любой раздел сайта.

Публикуются сразу, без регистрации — как форма правок и контактная форма
(honeypot-поле от спама), администрация модерирует только удалением
(см. app/routes/admin.py)."""
from flask import Blueprint, abort, flash, redirect, request, url_for

from app import db
from app.models import (
    Article,
    Book,
    DeliveryService,
    Equipment,
    Experiment,
    Review,
    SacredSource,
    WaterBrand,
)

bp = Blueprint("reviews", __name__)

MAX_BODY_LENGTH = 4000

# Куда вести объект каждого типа и как построить на него ссылку — все
# модели-цели используют SlugMixin, поэтому редирект строится одинаково.
REVIEW_TARGETS = {
    "sacred_source": {"model": SacredSource, "endpoint": "sacred.detail"},
    "water_brand": {"model": WaterBrand, "endpoint": "catalog.detail"},
    "equipment": {"model": Equipment, "endpoint": "main.equipment_detail"},
    "book": {"model": Book, "endpoint": "library.detail"},
    "article": {"model": Article, "endpoint": "articles.detail"},
    "experiment": {"model": Experiment, "endpoint": "main.experiment_detail"},
    "delivery_service": {"model": DeliveryService, "endpoint": "main.delivery_detail"},
}


def reviews_for(target_type, target_id):
    """Отзывы и средняя оценка объекта — используется в детальных роутах
    вместе с шаблоном templates/_reviews.html."""
    items = (
        Review.query.filter_by(target_type=target_type, target_id=target_id)
        .order_by(Review.created_at.desc())
        .all()
    )
    average = round(sum(r.rating for r in items) / len(items), 1) if items else None
    return items, average


@bp.route("/<target_type>/<int:target_id>", methods=["POST"])
def add(target_type, target_id):
    target_info = REVIEW_TARGETS.get(target_type)
    if target_info is None:
        abort(404)

    target = db.session.get(target_info["model"], target_id)
    if target is None:
        abort(404)

    redirect_url = url_for(target_info["endpoint"], slug=target.slug)

    # honeypot: скрытое от людей поле формы — если его заполнил бот, тихо
    # делаем вид, что всё отправилось, но ничего не сохраняем.
    if request.form.get("website"):
        flash("Спасибо за отзыв!", "success")
        return redirect(redirect_url)

    author_name = (request.form.get("author_name") or "").strip()
    body = (request.form.get("body") or "").strip()
    rating = request.form.get("rating", type=int)

    if not body:
        flash("Напишите текст отзыва.", "error")
        return redirect(redirect_url)
    if len(body) > MAX_BODY_LENGTH:
        flash("Отзыв слишком длинный.", "error")
        return redirect(redirect_url)
    if rating is None or not (1 <= rating <= 5):
        flash("Выберите оценку от 1 до 5.", "error")
        return redirect(redirect_url)

    review = Review(
        target_type=target_type,
        target_id=target_id,
        author_name=author_name or None,
        rating=rating,
        body=body,
    )
    db.session.add(review)
    db.session.commit()

    flash("Спасибо за отзыв!", "success")
    return redirect(redirect_url)
