"""Главная страница (открыта всем) и переключение языка интерфейса."""
import os

from flask import Blueprint, current_app, redirect, render_template, request, session, url_for
from flask_login import current_user

from app.decorators import paywall_required
from app.i18n import SUPPORTED_LANGUAGES

bp = Blueprint("main", __name__)

INTRO_VIDEO_FILENAME = "video/intro.mp4"


@bp.route("/")
def index():
    """Главная — единственная полностью открытая страница (модуль 1: «жёсткий»
    paywall). Если сюда пришёл редирект от paywall_required, показываем
    модальное окно регистрации/входа поверх главной."""
    from app.models import User

    auth_required = request.args.get("auth_required") == "1"
    next_url = request.args.get("next") or ""

    stats = {
        "customer": User.query.filter_by(role="customer").count(),
        "executor": User.query.filter_by(role="executor").count(),
        "constructor": User.query.filter_by(role="constructor").count(),
    }
    stats["total"] = stats["customer"] + stats["executor"] + stats["constructor"]

    # Видео на главной — «честная деградация»: пока администратор не залил
    # файл на сервер (через FTP, без правок кода), вместо баннера с видео
    # показываем заглушку с подсказкой, а не сломанный плеер.
    intro_video_available = os.path.isfile(os.path.join(current_app.static_folder, INTRO_VIDEO_FILENAME))

    return render_template(
        "main/index.html", auth_required=auth_required, next_url=next_url, stats=stats,
        intro_video_available=intro_video_available,
    )


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


@bp.route("/notifications")
@paywall_required
def notifications():
    from datetime import datetime

    from app import db
    from app.models import Notification

    items = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(100).all()
    unread_ids = [n.id for n in items if n.read_at is None]
    if unread_ids:
        Notification.query.filter(Notification.id.in_(unread_ids)).update(
            {"read_at": datetime.utcnow()}, synchronize_session=False
        )
        db.session.commit()
    return render_template("main/notifications.html", items=items)
