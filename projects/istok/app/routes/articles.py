"""Раздел «Статьи»."""
from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.models import Article
from app.photos import upload_photo
from app.routes.reviews import reviews_for
from app.slugify import unique_slug

bp = Blueprint("articles", __name__)


@bp.route("/")
def index():
    page = request.args.get("page", 1, type=int)
    per_page = current_app.config["ITEMS_PER_PAGE"]
    pagination = Article.query.order_by(Article.published_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return render_template("articles/index.html", pagination=pagination, articles=pagination.items)


@bp.route("/add", methods=["GET", "POST"])
@login_required
def add():
    if not current_user.email_confirmed:
        flash("Сначала подтвердите email — так мы защищаем каталог от спама.", "error")
        return redirect(url_for("articles.index"))

    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        category = (request.form.get("category") or "").strip()
        summary = (request.form.get("summary") or "").strip()
        body = (request.form.get("body") or "").strip()

        if not title or not category or not body:
            flash("Заполните название, рубрику и текст статьи.", "error")
            return render_template("articles/add.html")

        cover_url, photo_error = upload_photo(request.files.get("cover"))
        if photo_error:
            flash(photo_error, "info")

        used_slugs = {row[0] for row in db.session.query(Article.slug).all()}
        article = Article(
            slug=unique_slug(title, used_slugs, "article"),
            title=title,
            category=category,
            summary=summary or None,
            body=body,
            cover_url=cover_url,
            verified=False,
            added_by_user_id=current_user.id,
        )
        db.session.add(article)
        db.session.commit()

        flash(
            "Статья добавлена и уже видна на сайте с пометкой «не проверено» "
            "— администрация проверит и подтвердит.",
            "success",
        )
        return redirect(url_for("articles.detail", slug=article.slug))

    return render_template("articles/add.html")


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
