"""Раздел «Библиотека книг о воде»."""
from flask import Blueprint, render_template, request

from app.models import Book

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
