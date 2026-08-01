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
        db.session.add(
            WaterBrand(
                name="Тестовая вода",
                water_type="питьевая",
                mineralization_mg_l=200,
                volume_l=1.5,
                price_rub=50,
            )
        )
        db.session.add(
            Book(
                title="Тестовая книга",
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
                description="Описание тестового фильтра.",
            )
        )
        db.session.add(
            Experiment(
                title="Тестовый опыт",
                description="Описание тестового опыта.",
                verdict="наука",
            )
        )
        db.session.add(
            DeliveryService(
                name="Тестовая доставка",
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
