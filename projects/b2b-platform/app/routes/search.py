"""Поиск по сайту — по каталогам конструкторов, исполнителей, барахолки
станков, материалов и вакансий. Настройка «точное / частичное совпадение»
применяется к названию/имени и описанию каждой карточки.

Сравнение делается в Python (а не через SQL lower()/ILIKE): SQLite (тесты,
локальная разработка) приводит к нижнему регистру только ASCII и ломает
поиск по кириллице, а поведение ILIKE на PostgreSQL зависит от локали БД —
не хочется зависеть от этого. Каталоги на платформе некрупные, так что
фильтрация на стороне приложения не создаёт проблем с производительностью."""
from flask import Blueprint, render_template, request

from app.decorators import paywall_required
from app.models import ConstructorProfile, ExecutorProfile, Listing, MaterialListing, User, Vacancy

bp = Blueprint("search", __name__)

RESULTS_LIMIT = 30


def _text_match(*values, q, mode):
    """mode='exact' — хотя бы одно из полей совпадает целиком (без учёта
    регистра); mode='partial' (по умолчанию) — вхождение подстроки хотя бы
    в одно из полей."""
    q_lower = q.lower()
    for value in values:
        if not value:
            continue
        value_lower = value.lower()
        if mode == "exact":
            if value_lower == q_lower:
                return True
        elif q_lower in value_lower:
            return True
    return False


@bp.route("/search")
@paywall_required
def index():
    q = (request.args.get("q") or "").strip()
    mode = request.args.get("mode") if request.args.get("mode") in ("exact", "partial") else "partial"

    results = {"executors": [], "constructors": [], "listings": [], "materials": [], "vacancies": []}

    if q:
        executors = (
            ExecutorProfile.query.join(User, ExecutorProfile.user_id == User.id)
            .filter(User.role == "executor", ExecutorProfile.display_name.isnot(None))
            .order_by(ExecutorProfile.display_name).all()
        )
        results["executors"] = [
            e for e in executors if _text_match(e.display_name, e.description, q=q, mode=mode)
        ][:RESULTS_LIMIT]

        constructors = (
            ConstructorProfile.query.join(User, ConstructorProfile.user_id == User.id)
            .filter(User.role == "constructor", ConstructorProfile.display_name.isnot(None))
            .order_by(ConstructorProfile.display_name).all()
        )
        results["constructors"] = [
            c for c in constructors if _text_match(c.display_name, c.description, q=q, mode=mode)
        ][:RESULTS_LIMIT]

        listings = Listing.query.filter(Listing.status == "active").order_by(Listing.created_at.desc()).all()
        results["listings"] = [
            listing for listing in listings if _text_match(listing.title, listing.description, q=q, mode=mode)
        ][:RESULTS_LIMIT]

        materials = (
            MaterialListing.query.filter(MaterialListing.status == "active")
            .order_by(MaterialListing.created_at.desc()).all()
        )
        results["materials"] = [
            m for m in materials if _text_match(m.title, m.description, q=q, mode=mode)
        ][:RESULTS_LIMIT]

        vacancies = Vacancy.query.filter(Vacancy.status == "active").order_by(Vacancy.created_at.desc()).all()
        results["vacancies"] = [
            v for v in vacancies if _text_match(v.title, v.description, q=q, mode=mode)
        ][:RESULTS_LIMIT]

    total = sum(len(v) for v in results.values())
    return render_template("search/index.html", q=q, mode=mode, results=results, total=total)
