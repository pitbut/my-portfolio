"""Раздел «Статьи»."""
from flask import Blueprint, abort, current_app, render_template, request

from app.models import Article
from app.routes.reviews import reviews_for

bp = Blueprint("articles", __name__)


@bp.route("/")
def index():
    page = request.args.get("page", 1, type=int)
    per_page = current_app.config["ITEMS_PER_PAGE"]
    pagination = Article.query.order_by(Article.published_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return render_template("articles/index.html", pagination=pagination, articles=pagination.items)


@bp.route("/<slug>")
def detail(slug):
    article = Article.query.filter_by(slug=slug).first()
    if article is None:
        abort(404)
    reviews, avg_rating = reviews_for("article", article.id)
    return render_template(
        "articles/detail.html",
        article=article,
        reviews=reviews,
        avg_rating=avg_rating,
        target_type="article",
        target_id=article.id,
    )
