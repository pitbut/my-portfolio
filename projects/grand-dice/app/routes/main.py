"""Главная страница."""
from flask import Blueprint, current_app, redirect, render_template, request, session, url_for
from flask_login import current_user

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("game.play_page"))
    return render_template("main/index.html")


@bp.route("/lang/<code>")
def set_language(code):
    if code in current_app.config["LANGUAGES"]:
        session["lang"] = code
    next_url = request.referrer or url_for("main.index")
    return redirect(next_url)
