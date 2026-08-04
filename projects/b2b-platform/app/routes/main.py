"""Главная страница (открыта всем) и переключение языка интерфейса."""
from flask import Blueprint, redirect, render_template, request, session, url_for
from flask_login import current_user

from app.i18n import SUPPORTED_LANGUAGES

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    """Главная — единственная полностью открытая страница (модуль 1: «жёсткий»
    paywall). Если сюда пришёл редирект от paywall_required, показываем
    модальное окно регистрации/входа поверх главной."""
    auth_required = request.args.get("auth_required") == "1"
    next_url = request.args.get("next") or ""
    return render_template("main/index.html", auth_required=auth_required, next_url=next_url)


@bp.route("/lang/<lang>")
def set_language(lang):
    if lang not in SUPPORTED_LANGUAGES:
        lang = "ru"
    session["lang"] = lang
    if current_user.is_authenticated:
        from app import db

        current_user.preferred_language = lang
        db.session.commit()
    return redirect(request.referrer or url_for("main.index"))
