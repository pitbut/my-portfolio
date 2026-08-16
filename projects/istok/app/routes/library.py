"""Раздел «Библиотека книг о воде»."""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.models import Book
from app.photos import upload_photo
from app.routes.reviews import reviews_for
from app.slugify import unique_slug

bp = Blueprint("library", __name__)


@bp.route("/")
def index():
    genre = request.args.get("genre")
    query = Book.query
    if genre:
        query = query.filter_by(genre=genre)
    books = query.order_by(Book.year.desc(), Book.title).all()
    genres = [row[0] for row in Book.query.with_entities(Book.genre).distinct() if row[0]]
    return render_template("library/index.html", books=books, genres=genres, active_genre=genre)


@bp.route("/add", methods=["GET", "POST"])
@login_required
def add():
    if not current_user.email_confirmed:
        flash("Сначала подтвердите email — так мы защищаем каталог от спама.", "error")
        return redirect(url_for("library.index"))

    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        author = (request.form.get("author") or "").strip()
        year = request.form.get("year") or None
        genre = (request.form.get("genre") or "").strip()
        description = (request.form.get("description") or "").strip()

        if not title or not author or not description:
            flash("Заполните название, автора и описание.", "error")
            return render_template("library/add.html")

        try:
            year = int(year) if year else None
        except ValueError:
            year = None

        cover_url, photo_error = upload_photo(request.files.get("cover"))
        if photo_error:
            flash(photo_error, "info")

        used_slugs = {row[0] for row in db.session.query(Book.slug).all()}
        book = Book(
            slug=unique_slug(title, used_slugs, "book"),
            title=title,
            author=author,
            year=year,
            genre=genre or None,
            description=description,
            cover_url=cover_url,
            verified=False,
            added_by_user_id=current_user.id,
        )
        db.session.add(book)
        db.session.commit()

        flash(
            "Книга добавлена и уже видна в библиотеке с пометкой «не проверено» "
            "— администрация проверит и подтвердит.",
            "success",
        )
        return redirect(url_for("library.detail", slug=book.slug))

    return render_template("library/add.html")


@bp.route("/<slug>")
def detail(slug):
    book = Book.query.filter_by(slug=slug).first()
    if book is None:
        abort(404)
    reviews, avg_rating = reviews_for("book", book.id)
    return render_template(
        "library/detail.html",
        book=book,
        reviews=reviews,
        avg_rating=avg_rating,
        target_type="book",
        target_id=book.id,
    )
