"""Наполняет базу данных данными из CSV-файлов в data/.

Запуск: python seed.py

По умолчанию скрипт заполняет из CSV только ПУСТЫЕ таблицы — если в
таблице уже есть данные (например, после первого запуска, или после
правок, одобренных через /admin), она не трогается. Это специально:
иначе правки, одобренные модератором в веб-панели, стирались бы при
каждом деплое/рестарте сервера.

Если нужно принудительно стереть и перезалить всё заново из CSV
(например, вы отредактировали много строк в CSV и хотите синхронизировать
базу) — установите переменную окружения FORCE_RESEED=true. Учтите: это
сотрёт и все одобренные через /admin правки, сделанные после последней
синхронизации с CSV.
"""
import csv
from datetime import datetime
from pathlib import Path

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

DATA_DIR = Path(__file__).resolve().parent / "data"


def read_csv(filename):
    path = DATA_DIR / filename
    # utf-8-sig корректно читает файл и с BOM (его добавляет Excel при
    # сохранении), и без — оба варианта нужны, т.к. CSV правят и в Excel,
    # и через редактор GitHub.
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def clean(value):
    """Пустая строка из CSV -> None, иначе строка без лишних пробелов."""
    if value is None:
        return None
    value = value.strip()
    return value or None


def to_int(value):
    value = clean(value)
    return int(value) if value is not None else None


def to_float(value):
    value = clean(value)
    return float(value) if value is not None else None


def to_decimal_str(value):
    """Для полей Numeric достаточно передать строку/число — SQLAlchemy сконвертирует."""
    value = clean(value)
    return value


def to_date(value):
    value = clean(value)
    return datetime.strptime(value, "%Y-%m-%d") if value is not None else None


def load_sacred_sources():
    for row in read_csv("sacred_sources.csv"):
        yield SacredSource(
            slug=row["slug"].strip(),
            name=row["name"].strip(),
            country=row["country"].strip(),
            location=row["location"].strip(),
            latitude=to_float(row.get("latitude")),
            longitude=to_float(row.get("longitude")),
            annual_visitors=to_int(row.get("annual_visitors")),
            belief=row["belief"].strip(),
            allowed=row["allowed"].strip(),
            forbidden=row["forbidden"].strip(),
            description=clean(row.get("description")),
            image_url=clean(row.get("image_url")),
            comment=clean(row.get("comment")),
        )


def load_books():
    for row in read_csv("books.csv"):
        yield Book(
            title=row["title"].strip(),
            author=row["author"].strip(),
            year=to_int(row.get("year")),
            genre=clean(row.get("genre")),
            description=row["description"].strip(),
            cover_url=clean(row.get("cover_url")),
        )


def load_articles():
    for row in read_csv("articles.csv"):
        yield Article(
            slug=row["slug"].strip(),
            title=row["title"].strip(),
            category=row["category"].strip(),
            summary=clean(row.get("summary")),
            body=row["body"].strip(),
            published_at=to_date(row.get("published_at")) or datetime.utcnow(),
            cover_url=clean(row.get("cover_url")),
        )


def load_water_brands():
    for row in read_csv("water_brands.csv"):
        yield WaterBrand(
            name=row["name"].strip(),
            water_type=row["water_type"].strip(),
            mineralization_mg_l=to_int(row.get("mineralization_mg_l")),
            volume_l=to_decimal_str(row["volume_l"]),
            price_rub=to_decimal_str(row["price_rub"]),
            origin=clean(row.get("origin")),
        )


def load_equipment():
    for row in read_csv("equipment.csv"):
        yield Equipment(
            category=row["category"].strip(),
            name=row["name"].strip(),
            description=row["description"].strip(),
            price_rub=to_decimal_str(row.get("price_rub")),
            manufacturer=clean(row.get("manufacturer")),
        )


def load_experiments():
    for row in read_csv("experiments.csv"):
        yield Experiment(
            title=row["title"].strip(),
            description=row["description"].strip(),
            verdict=row["verdict"].strip(),
        )


def load_delivery_services():
    for row in read_csv("delivery_services.csv"):
        yield DeliveryService(
            name=row["name"].strip(),
            coverage=clean(row.get("coverage")),
            delivery_time=row["delivery_time"].strip(),
            price_rub=to_decimal_str(row.get("price_rub")),
            phone=clean(row.get("phone")),
            website=clean(row.get("website")),
        )


MODEL_LOADERS = [
    (SacredSource, load_sacred_sources, "источников"),
    (Book, load_books, "книг"),
    (Article, load_articles, "статей"),
    (WaterBrand, load_water_brands, "марок воды"),
    (Equipment, load_equipment, "единиц оборудования"),
    (Experiment, load_experiments, "опытов"),
    (DeliveryService, load_delivery_services, "служб доставки"),
]


def seed():
    app = create_app()
    with app.app_context():
        force = app.config.get("FORCE_RESEED", False)

        if force:
            db.drop_all()
        db.create_all()

        loaded, skipped = {}, []
        for model, loader, label in MODEL_LOADERS:
            if not force and model.query.count() > 0:
                skipped.append(label)
                continue
            n = 0
            for obj in loader():
                db.session.add(obj)
                n += 1
            loaded[label] = n

        db.session.commit()

        if loaded:
            print("Загружено из CSV: " + ", ".join(f"{n} {label}" for label, n in loaded.items()))
        if skipped:
            print("Пропущено (в базе уже есть данные): " + ", ".join(skipped))
        if not loaded and not skipped:
            print("Нечего загружать.")


if __name__ == "__main__":
    seed()
