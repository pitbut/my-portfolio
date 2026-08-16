import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from app import create_app, db
from app.models import (
    Article,
    Book,
    DeliveryService,
    Equipment,
    Experiment,
    SacredSource,
    Supplier,
    WaterBrand,
)


@pytest.fixture()
def app():
    app = create_app("testing")

    with app.app_context():
        db.create_all()

        db.session.add(
            SacredSource(
                name="Тестовый источник",
                slug="test-source",
                country="Тестландия",
                location="где-то у реки",
                belief="Люди верят, что вода исполняет желания.",
                allowed="Набирать воду в бутылки.",
                forbidden="Купаться с мылом.",
                annual_visitors=1000,
                image_url="sacred/test-source.jpg",
                comment="Тестовый комментарий редакции.",
            )
        )
        db.session.add(
            Article(
                title="Тестовая статья",
                slug="test-article",
                category="Наука",
                summary="Краткое содержание тестовой статьи.",
                body="Первый абзац.\n\nВторой абзац.",
            )
        )
        water_brand = WaterBrand(
            name="Тестовая вода",
            slug="test-water",
            water_type="питьевая",
            mineralization_mg_l=200,
            volume_l=1.5,
            price=50,
            currency="RUB",
            country="Россия",
            description="Описание тестовой воды.",
        )
        db.session.add(water_brand)
        db.session.add(
            WaterBrand(
                name="Тестовая вода 2",
                slug="test-water-2",
                water_type="природная негазированная",
                volume_l=1.0,
                price=3000,
                currency="UZS",
                country="Узбекистан",
                description="Вторая тестовая марка для проверки фильтра по стране.",
            )
        )
        db.session.flush()
        db.session.add(
            Supplier(
                water_brand_id=water_brand.id,
                name="Тестовый поставщик",
                supplier_type="опт",
                address="Тестовая ул., 1",
                latitude=55.75,
                longitude=37.61,
                verified=True,
            )
        )
        db.session.add(
            Book(
                title="Тестовая книга",
                slug="test-book",
                author="Автор Тестов",
                year=2020,
                genre="наука",
                description="Описание тестовой книги.",
            )
        )
        db.session.add(
            Equipment(
                category="Фильтр",
                name="Тестовый фильтр",
                slug="test-filter",
                description="Описание тестового фильтра.",
                verified=True,
            )
        )
        db.session.add(
            Experiment(
                title="Тестовый опыт",
                slug="test-experiment",
                description="Описание тестового опыта.",
                verdict="наука",
            )
        )
        db.session.add(
            DeliveryService(
                name="Тестовая доставка",
                slug="test-delivery",
                delivery_time="1 день",
            )
        )
        db.session.commit()

        yield app

        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()
