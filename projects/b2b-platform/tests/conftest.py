import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from app import create_app, db
from app.models import (
    EquipmentType,
    ListingCategory,
    Material,
    MaterialForm,
    ProfessionCategory,
    Region,
    ServiceCategory,
    SubscriptionPlan,
)


@pytest.fixture()
def app():
    app = create_app("testing")

    with app.app_context():
        db.create_all()

        region = Region(
            name_ru="Ташкентская область", name_uz_latin="Toshkent viloyati",
            name_uz_cyrillic="Тошкент вилояти", latitude=41.0, longitude=69.3,
        )
        db.session.add(region)
        db.session.add(EquipmentType(
            name_ru="Токарный станок с ЧПУ", name_uz_latin="CPU tokarlik stanogi",
            name_uz_cyrillic="ЧПУ токарлик станоги",
        ))
        db.session.add(ServiceCategory(
            name_ru="Токарные работы", name_uz_latin="Tokarlik ishlari", name_uz_cyrillic="Токарлик ишлари",
        ))
        db.session.add(Material(
            name_ru="Сталь конструкционная", name_uz_latin="Konstruksion po'lat", name_uz_cyrillic="Конструкцион пўлат",
        ))
        db.session.add(ListingCategory(
            name_ru="Станки с ЧПУ", name_uz_latin="CPU stanoklar", name_uz_cyrillic="ЧПУ станоклар",
        ))
        db.session.add(ProfessionCategory(
            name_ru="Токарь", name_uz_latin="Tokar", name_uz_cyrillic="Токар",
        ))
        db.session.add(MaterialForm(
            name_ru="Лист", name_uz_latin="List", name_uz_cyrillic="Лист",
        ))
        db.session.add(SubscriptionPlan(code="basic", title="Basic", price_monthly_uzs=150000, max_bids_per_month=10, telegram_alert_delay_minutes=120, catalog_priority=1))
        db.session.add(SubscriptionPlan(code="standard", title="Standard", price_monthly_uzs=350000, max_bids_per_month=40, telegram_alert_delay_minutes=0, catalog_priority=5))
        db.session.add(SubscriptionPlan(code="pro", title="Pro", price_monthly_uzs=700000, max_bids_per_month=None, telegram_alert_delay_minutes=0, catalog_priority=10))
        db.session.commit()

        yield app

        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def register(client, email="user@example.com", password="password123", role="customer", confirm_email=True):
    """confirm_email=True (по умолчанию) сразу подтверждает почту тестовому
    пользователю — большинству тестов не важен сам процесс подтверждения,
    важно, чтобы дальше можно было создавать заявки/ставки/отклики и т.п.
    (теперь требующие email_confirmed=True, см. email_confirmed_required).
    Тесты, которые проверяют именно процесс подтверждения, передают
    confirm_email=False."""
    resp = client.post(
        "/auth/register",
        data={
            "email": email, "password": password, "password2": password,
            "role": role, "language": "ru", "next": "",
        },
        follow_redirects=True,
    )
    if confirm_email:
        with client.application.app_context():
            from app.models import User

            user = User.query.filter_by(email=email).first()
            if user is not None:
                user.email_confirmed = True
                db.session.commit()
    return resp
