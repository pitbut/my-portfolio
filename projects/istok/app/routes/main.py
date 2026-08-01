"""Главная страница и разделы без собственного блюпринта (оборудование,
опыты, доставка) — по одному-два на раздел, без пагинации."""
from flask import Blueprint, render_template

from app.models import (
    Article,
    Book,
    DeliveryService,
    Equipment,
    Experiment,
    SacredSource,
    WaterBrand,
)

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    sacred_sources = SacredSource.query.order_by(SacredSource.name).limit(3).all()
    articles = Article.query.order_by(Article.published_at.desc()).limit(3).all()
    water_brands = WaterBrand.query.order_by(WaterBrand.price_rub).limit(4).all()
    books = Book.query.order_by(Book.created_at.desc()).limit(3).all()
    equipment = Equipment.query.order_by(Equipment.created_at.desc()).limit(3).all()
    experiments = Experiment.query.order_by(Experiment.created_at.desc()).limit(3).all()
    delivery_services = DeliveryService.query.order_by(DeliveryService.name).limit(3).all()

    return render_template(
        "main/index.html",
        sacred_sources=sacred_sources,
        articles=articles,
        water_brands=water_brands,
        books=books,
        equipment=equipment,
        experiments=experiments,
        delivery_services=delivery_services,
    )


@bp.route("/equipment")
def equipment_list():
    category = None
    query = Equipment.query.order_by(Equipment.category, Equipment.name)
    equipment = query.all()
    return render_template("main/equipment.html", equipment=equipment, category=category)


@bp.route("/experiments")
def experiments_list():
    experiments = Experiment.query.order_by(Experiment.title).all()
    return render_template("main/experiments.html", experiments=experiments)


@bp.route("/delivery")
def delivery_list():
    services = DeliveryService.query.order_by(DeliveryService.name).all()
    return render_template("main/delivery.html", services=services)
