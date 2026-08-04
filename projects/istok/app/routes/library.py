"""Раздел «Библиотека книг о воде»."""
from flask import Blueprint, abort, render_template, request

from app.models import Book
from app.routes.reviews import reviews_for

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
