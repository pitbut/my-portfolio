"""Наполняет справочники (регионы, города, оборудование, услуги, материалы)
данными из CSV в data/. Запуск: python seed.py

Заполняет только ПУСТЫЕ таблицы — повторный запуск на уже заполненной базе
ничего не делает и безопасен (в отличие от истории пользователей/профилей,
которую скрипт вообще не трогает)."""
import csv
from pathlib import Path

from app import create_app, db
from app.models import (
    City,
    EquipmentType,
    ListingCategory,
    Material,
    MaterialForm,
    ProfessionCategory,
    Region,
    ServiceCategory,
    SubscriptionPlan,
)

DATA_DIR = Path(__file__).resolve().parent / "data"


def read_csv(filename):
    with open(DATA_DIR / filename, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def seed_regions():
    if Region.query.first() is not None:
        print("regions уже заполнены — пропускаю")
        return
    for row in read_csv("regions.csv"):
        db.session.add(Region(
            name_ru=row["name_ru"],
            name_uz_latin=row["name_uz_latin"],
            name_uz_cyrillic=row["name_uz_cyrillic"],
            latitude=float(row["latitude"]),
            longitude=float(row["longitude"]),
        ))
    db.session.commit()
    print(f"regions: добавлено {Region.query.count()}")


def seed_cities():
    if City.query.first() is not None:
        print("cities уже заполнены — пропускаю")
        return
    regions_by_name = {r.name_ru: r for r in Region.query.all()}
    for row in read_csv("cities.csv"):
        region = regions_by_name.get(row["region_name_ru"])
        if region is None:
            print(f"  ! регион не найден для города {row['name_ru']!r}, пропускаю")
            continue
        db.session.add(City(
            region_id=region.id,
            name_ru=row["name_ru"],
            name_uz_latin=row["name_uz_latin"],
            name_uz_cyrillic=row["name_uz_cyrillic"],
            latitude=float(row["latitude"]),
            longitude=float(row["longitude"]),
        ))
    db.session.commit()
    print(f"cities: добавлено {City.query.count()}")


def seed_simple_dictionary(model, filename):
    """Добавляет в справочник строки из CSV, которых там ещё нет (по
    name_ru) — не просто «пусто -> заполнить один раз», а безопасный
    повторный запуск: новые строки, дописанные в CSV позже, подтянутся при
    следующем деплое сами, а уже существующие не дублируются."""
    existing_names = {row.name_ru for row in model.query.all()}
    added = 0
    for row in read_csv(filename):
        if row["name_ru"] in existing_names:
            continue
        db.session.add(model(
            name_ru=row["name_ru"],
            name_uz_latin=row["name_uz_latin"],
            name_uz_cyrillic=row["name_uz_cyrillic"],
        ))
        added += 1
    db.session.commit()
    print(f"{model.__tablename__}: добавлено новых {added}, всего {model.query.count()}")


def seed_subscription_plans():
    if SubscriptionPlan.query.filter(SubscriptionPlan.code != "trial").first() is not None:
        print("subscription_plans (платные) уже заполнены — пропускаю")
        return
    plans = [
        dict(code="basic", title="Basic", price_monthly_uzs=150000, max_bids_per_month=10,
             telegram_alert_delay_minutes=120, catalog_priority=1),
        dict(code="standard", title="Standard", price_monthly_uzs=350000, max_bids_per_month=40,
             telegram_alert_delay_minutes=0, catalog_priority=5),
        dict(code="pro", title="Pro", price_monthly_uzs=700000, max_bids_per_month=None,
             telegram_alert_delay_minutes=0, catalog_priority=10),
    ]
    for data in plans:
        db.session.add(SubscriptionPlan(**data))
    db.session.commit()
    print(f"subscription_plans: добавлено {len(plans)}")


def main():
    app = create_app()
    with app.app_context():
        db.create_all()
        seed_regions()
        seed_cities()
        seed_simple_dictionary(EquipmentType, "equipment_types.csv")
        seed_simple_dictionary(ServiceCategory, "service_categories.csv")
        seed_simple_dictionary(Material, "materials.csv")
        seed_simple_dictionary(ListingCategory, "listing_categories.csv")
        seed_simple_dictionary(ProfessionCategory, "profession_categories.csv")
        seed_simple_dictionary(MaterialForm, "material_forms.csv")
        seed_subscription_plans()
        print("Готово.")


if __name__ == "__main__":
    main()
