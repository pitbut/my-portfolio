"""Главная страница (открыта всем) и переключение языка интерфейса."""
import os

from flask import Blueprint, current_app, redirect, render_template, request, session, url_for
from flask_login import current_user

from app.decorators import paywall_required
from app.i18n import SUPPORTED_LANGUAGES

bp = Blueprint("main", __name__)

INTRO_VIDEO_FILENAME = "video/intro.mp4"
# Универсальный рекламный баннер: подходит и видео, и картинка — что найдётся
# первым (в этом порядке), то и покажется. Видео проверяется первым, чтобы
# при наличии обоих файлов сразу после смены рекламы не подхватилась старая
# картинка, если видео залито тем же именем набора позже.
AD_BANNER_VIDEO_FILENAMES = ("ad/banner.mp4",)
AD_BANNER_IMAGE_FILENAMES = ("ad/banner.jpg", "ad/banner.jpeg", "ad/banner.png", "ad/banner.gif")


def _find_ad_banner():
    for filename in AD_BANNER_VIDEO_FILENAMES:
        if os.path.isfile(os.path.join(current_app.static_folder, filename)):
            return "video", filename
    for filename in AD_BANNER_IMAGE_FILENAMES:
        if os.path.isfile(os.path.join(current_app.static_folder, filename)):
            return "image", filename
    return None, None


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

    # Видео и рекламный баннер на главной — «честная деградация»: пока
    # администратор не залил файл на сервер (через FTP, без правок кода),
    # вместо баннера показываем заглушку с подсказкой, а не сломанную ссылку.
    intro_video_available = os.path.isfile(os.path.join(current_app.static_folder, INTRO_VIDEO_FILENAME))
    ad_banner_kind, ad_banner_filename = _find_ad_banner()

    return render_template(
        "main/index.html", auth_required=auth_required, next_url=next_url, stats=stats,
        intro_video_available=intro_video_available,
        ad_banner_kind=ad_banner_kind, ad_banner_filename=ad_banner_filename,
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


_ROBOTS_TXT = """User-agent: *
Disallow: /lang/
Disallow: /*?auth_required=*
Disallow: /auth/logout
Disallow: /auth/confirm/
Disallow: /auth/reset-password/
Disallow: /auth/google/
Disallow: /auth/choose-role
Disallow: /profile/
Disallow: /orders/
Disallow: /dashboard
Disallow: /messages/
Disallow: /settings/
Disallow: /admin/
Disallow: /map
Disallow: /search
Disallow: /constructors/
Disallow: /marketplace/
Disallow: /materials/
Disallow: /jobs/
Disallow: /disputes/
Disallow: /reviews/
Disallow: /push/
Disallow: /telegram/
Disallow: /notifications

Sitemap: {sitemap_url}
"""


def _public_base_url():
    """Публичный домен для абсолютных ссылок в robots.txt/sitemap.xml — берём
    из PUBLIC_BASE_URL, если задан (см. config.py), иначе строим из самого
    запроса (для локальной разработки, где эта переменная не нужна)."""
    configured = current_app.config.get("PUBLIC_BASE_URL")
    return (configured or request.url_root).rstrip("/")


@bp.route("/robots.txt")
def robots_txt():
    """Без этого файла поисковики ползают по всем ссылкам подряд, включая
    служебные (/lang/..., переключение языка) и закрытые логином разделы
    (объявления, анкеты, заявки и т.п.) — те всё равно отдают анонимному
    боту редирект на главную, поэтому индексировать там нечего."""
    body = _ROBOTS_TXT.format(sitemap_url=f"{_public_base_url()}/sitemap.xml")
    return current_app.response_class(body, mimetype="text/plain")


@bp.route("/sitemap.xml")
def sitemap_xml():
    """Реально публичных страниц у сайта немного — из-за «жёсткого paywall»
    (модуль 1 ТЗ) весь предметный контент открывается только после входа.
    Список специально короткий и честный, а не список всего подряд."""
    base = _public_base_url()
    pages = [
        (base + "/", "daily", "1.0"),
        (base + url_for("auth.register"), "monthly", "0.8"),
        (base + url_for("auth.login"), "monthly", "0.5"),
    ]
    entries = "\n".join(
        f"  <url><loc>{loc}</loc><changefreq>{freq}</changefreq><priority>{priority}</priority></url>"
        for loc, freq, priority in pages
    )
    xml = f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{entries}\n</urlset>\n'
    return current_app.response_class(xml, mimetype="application/xml")


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
