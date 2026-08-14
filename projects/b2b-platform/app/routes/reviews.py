"""Модуль 5 — двусторонние отзывы и рейтинги."""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user

from app import db
from app.decorators import email_confirmed_required, paywall_required
from app.models import Order, Review
from app.notify import notify

bp = Blueprint("reviews", __name__)


def _order_parties(order):
    """Возвращает (customer_user, executor_user) для завершённого заказа."""
    customer_user = order.customer.user
    executor_user = order.assignment.bid.executor.user if order.assignment else None
    return customer_user, executor_user


def _my_role_in_order(order):
    customer_user, executor_user = _order_parties(order)
    if current_user.id == customer_user.id:
        return "customer_to_executor", executor_user
    if executor_user is not None and current_user.id == executor_user.id:
        return "executor_to_customer", customer_user
    return None, None


def _recalculate_rating(user):
    """Пересчитывает rating_avg/reviews_count в профиле пользователя по
    опубликованным отзывам."""
    published = Review.query.filter_by(target_id=user.id, is_published=True).all()
    profile = user.customer_profile or user.executor_profile
    if profile is None:
        return
    if published:
        profile.rating_avg = round(sum(r.rating for r in published) / len(published), 2)
    else:
        profile.rating_avg = None
    profile.reviews_count = len(published)


@bp.route("/orders/<int:order_id>/review", methods=["GET", "POST"])
@paywall_required
@email_confirmed_required
def leave_review(order_id):
    order = db.session.get(Order, order_id)
    if order is None:
        abort(404)
    if order.status != "completed":
        flash("Оставить отзыв можно только после завершения заказа.", "error")
        return redirect(url_for("orders.order_detail", order_id=order.id))

    direction, target_user = _my_role_in_order(order)
    if direction is None:
        abort(403)

    existing = Review.query.filter_by(order_id=order.id, author_id=current_user.id).first()

    if request.method == "POST":
        rating = request.form.get("rating", type=int)
        comment = (request.form.get("comment") or "").strip() or None
        if not rating or not (1 <= rating <= 5):
            flash("Поставьте оценку от 1 до 5.", "error")
            return render_template("reviews/form.html", order=order, existing=existing)

        if existing is None:
            existing = Review(order_id=order.id, author_id=current_user.id, target_id=target_user.id, direction=direction)
            db.session.add(existing)
        existing.rating = rating
        existing.comment = comment
        db.session.flush()

        opposite = Review.query.filter(Review.order_id == order.id, Review.author_id == target_user.id).first()
        if opposite is not None:
            existing.is_published = True
            opposite.is_published = True
            _recalculate_rating(existing.target)
            _recalculate_rating(opposite.target)
            notify(
                target_user, "review_received", title="Опубликован новый отзыв о вас",
                body=f"Оценка: {existing.rating}/5", url=url_for("reviews.my_reviews"),
            )
            notify(
                current_user, "review_received", title="Опубликован новый отзыв о вас",
                body=f"Оценка: {opposite.rating}/5", url=url_for("reviews.my_reviews"),
            )
            flash("Спасибо! Оба отзыва опубликованы.", "success")
        else:
            flash("Отзыв сохранён и будет опубликован, как только своё мнение оставит другая сторона.", "info")

        db.session.commit()
        return redirect(url_for("orders.order_detail", order_id=order.id))

    return render_template("reviews/form.html", order=order, existing=existing)


@bp.route("/reviews")
@paywall_required
def my_reviews():
    received = (
        Review.query.filter_by(target_id=current_user.id, is_published=True)
        .order_by(Review.created_at.desc()).all()
    )
    given = Review.query.filter_by(author_id=current_user.id).order_by(Review.created_at.desc()).all()
    return render_template("reviews/list.html", received=received, given=given)
