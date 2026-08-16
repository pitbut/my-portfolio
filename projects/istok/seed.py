"""Наполняет базу данных данными из CSV-файлов в data/.

Запуск: python seed.py

Разделы с человекочитаемым slug (источники, книги, статьи, марки воды,
оборудование, опыты, службы доставки) синхронизируются построчно по slug
на КАЖДОМ запуске: строки CSV, которых ещё нет в базе, добавляются, а уже
существующие строки не трогаются — так можно просто дописывать новые
строки в CSV и деплоить, они появятся сами, а правки, одобренные через
/admin, не стираются.

Точки продажи (Supplier) не имеют стабильного природного ключа для такой
сверки, поэтому для них сохранено старое поведение: CSV загружается только
если таблица совсем пустая.

Если нужно принудительно стереть и перезалить всё заново из CSV (например,
вы отредактировали текст уже существующих строк и хотите синхронизировать
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
    Supplier,
    WaterBrand,
)
from app.slugify import unique_slug

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
    used_slugs = set()
    for row in read_csv("books.csv"):
        title = row["title"].strip()
        yield Book(
            slug=unique_slug(title, used_slugs, "book"),
            title=title,
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
            slug=row["slug"].strip(),
            name=row["name"].strip(),
            water_type=row["water_type"].strip(),
            mineralization_mg_l=to_int(row.get("mineralization_mg_l")),
            volume_l=to_decimal_str(row["volume_l"]),
            price=to_decimal_str(row["price"]),
            currency=(clean(row.get("currency")) or "RUB"),
            country=clean(row.get("country")),
            origin=clean(row.get("origin")),
            description=clean(row.get("description")),
            verified=True,
        )


def to_bool(value):
    return (clean(value) or "").lower() in ("true", "1", "yes", "да")


def load_suppliers():
    for row in read_csv("suppliers.csv"):
        brand = WaterBrand.query.filter_by(slug=row["water_brand_slug"].strip()).first()
        if brand is None:
            # марка не найдена (например, опечатка в CSV) — пропускаем
            # строку вместо падения всего сида.
            continue
        yield Supplier(
            water_brand_id=brand.id,
            name=row["name"].strip(),
            supplier_type=clean(row.get("supplier_type")),
            address=row["address"].strip(),
            latitude=to_float(row.get("latitude")),
            longitude=to_float(row.get("longitude")),
            phone=clean(row.get("phone")),
            website=clean(row.get("website")),
            verified=to_bool(row.get("verified")),
        )


def load_equipment():
    used_slugs = set()
    for row in read_csv("equipment.csv"):
        name = row["name"].strip()
        yield Equipment(
            slug=unique_slug(name, used_slugs, "equipment"),
            category=row["category"].strip(),
            name=name,
            description=row["description"].strip(),
            price_rub=to_decimal_str(row.get("price_rub")),
            manufacturer=clean(row.get("manufacturer")),
            verified=True,  # из CSV — куратор сайта, а не пользователь
        )


def load_experiments():
    used_slugs = set()
    for row in read_csv("experiments.csv"):
        title = row["title"].strip()
        yield Experiment(
            slug=unique_slug(title, used_slugs, "experiment"),
            title=title,
            description=row["description"].strip(),
            verdict=row["verdict"].strip(),
        )


def load_delivery_services():
    used_slugs = set()
    for row in read_csv("delivery_services.csv"):
        name = row["name"].strip()
        yield DeliveryService(
            slug=unique_slug(name, used_slugs, "service"),
            name=name,
            coverage=clean(row.get("coverage")),
            delivery_time=row["delivery_time"].strip(),
            price_rub=to_decimal_str(row.get("price_rub")),
            phone=clean(row.get("phone")),
            website=clean(row.get("website")),
        )


# Модели со slug — синхронизируются построчно на каждом запуске (новые
# строки CSV добавляются, существующие не трогаются). Порядок важен:
# WaterBrand должна обрабатываться до Supplier, который ищет её по slug.
SLUG_MODEL_LOADERS = [
    (SacredSource, load_sacred_sources, "источников"),
    (Book, load_books, "книг"),
    (Article, load_articles, "статей"),
    (WaterBrand, load_water_brands, "марок воды"),
    (Equipment, load_equipment, "единиц оборудования"),
    (Experiment, load_experiments, "опытов"),
    (DeliveryService, load_delivery_services, "служб доставки"),
]

# Модели без стабильного природного ключа — загружаются из CSV только
# если таблица совсем пустая (как раньше).
EMPTY_ONLY_LOADERS = [
    (Supplier, load_suppliers, "точек продажи"),
]


def seed():
    app = create_app()
    with app.app_context():
        force = app.config.get("FORCE_RESEED", False)

        if force:
            db.drop_all()
        db.create_all()

        added, skipped = {}, []

        for model, loader, label in SLUG_MODEL_LOADERS:
            if force:
                n = 0
                for obj in loader():
                    db.session.add(obj)
                    n += 1
            else:
                existing_slugs = {row[0] for row in db.session.query(model.slug).all()}
                n = 0
                for obj in loader():
                    if obj.slug in existing_slugs:
                        continue
                    db.session.add(obj)
                    existing_slugs.add(obj.slug)
                    n += 1
            db.session.flush()  # чтобы Supplier видел id марок воды (новых и уже существующих)
            if n:
                added[label] = n

        for model, loader, label in EMPTY_ONLY_LOADERS:
            if not force and model.query.count() > 0:
                skipped.append(label)
                continue
            n = 0
            for obj in loader():
                db.session.add(obj)
                n += 1
            db.session.flush()
            if n:
                added[label] = n

        db.session.commit()

        if added:
            print("Добавлено новых из CSV: " + ", ".join(f"{n} {label}" for label, n in added.items()))
        if skipped:
            print("Пропущено (в базе уже есть данные): " + ", ".join(skipped))
        if not added and not skipped:
            print("Нечего загружать — все данные уже в базе.")


if __name__ == "__main__":
    seed()
