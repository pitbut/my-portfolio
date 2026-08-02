"""SQLAlchemy-модели портала "Исток".

Общие для всех моделей поля вынесены в миксины TimestampMixin и SlugMixin,
чтобы новые разделы можно было добавлять без переписывания существующих.
Типы полей намеренно выбраны совместимыми и с SQLite, и с PostgreSQL —
никаких SQLite-специфичных типов здесь нет.
"""
from datetime import datetime

from app import db


class TimestampMixin:
    """Добавляет created_at/updated_at любой модели."""

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class SlugMixin:
    """Добавляет человекочитаемый slug для построения URL."""

    slug = db.Column(db.String(220), unique=True, nullable=False, index=True)


class Book(TimestampMixin, db.Model):
    """Книга о воде — раздел «Библиотека»."""

    __tablename__ = "books"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    author = db.Column(db.String(255), nullable=False)
    year = db.Column(db.Integer, nullable=True)
    genre = db.Column(db.String(120), nullable=True)
    description = db.Column(db.Text, nullable=False)
    cover_url = db.Column(db.String(500), nullable=True)

    def __repr__(self):
        return f"<Book {self.title!r} ({self.author})>"


class Article(TimestampMixin, SlugMixin, db.Model):
    """Статья — раздел «Статьи»."""

    __tablename__ = "articles"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(120), nullable=False)  # рубрика/тег
    summary = db.Column(db.String(500), nullable=True)
    body = db.Column(db.Text, nullable=False)
    published_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    cover_url = db.Column(db.String(500), nullable=True)

    def __repr__(self):
        return f"<Article {self.title!r}>"


class WaterBrand(TimestampMixin, db.Model):
    """Марка питьевой воды — раздел «Каталог цен»."""

    __tablename__ = "water_brands"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    water_type = db.Column(db.String(120), nullable=False)  # питьевая/минеральная/родниковая...
    mineralization_mg_l = db.Column(db.Integer, nullable=True)  # мг/л
    volume_l = db.Column(db.Numeric(5, 2), nullable=False)
    price_rub = db.Column(db.Numeric(10, 2), nullable=False)
    origin = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f"<WaterBrand {self.name!r}>"


class SacredSource(TimestampMixin, SlugMixin, db.Model):
    """Священный источник — раздел «Священные источники мира»."""

    __tablename__ = "sacred_sources"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    country = db.Column(db.String(120), nullable=False)
    location = db.Column(db.String(255), nullable=False)  # текстовое описание места
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    belief = db.Column(db.Text, nullable=False)  # во что верят люди
    allowed = db.Column(db.Text, nullable=False)  # что можно
    forbidden = db.Column(db.Text, nullable=False)  # что нельзя
    annual_visitors = db.Column(db.Integer, nullable=True)  # посещаемость в год
    image_url = db.Column(db.String(500), nullable=True)
    description = db.Column(db.Text, nullable=True)
    comment = db.Column(db.Text, nullable=True)  # произвольный комментарий редактора

    def __repr__(self):
        return f"<SacredSource {self.name!r} ({self.country})>"


class Equipment(TimestampMixin, db.Model):
    """Оборудование для воды — фильтры/кулеры/счётчики."""

    __tablename__ = "equipment"

    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(120), nullable=False)  # фильтр/кулер/счётчик
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price_rub = db.Column(db.Numeric(10, 2), nullable=True)
    manufacturer = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f"<Equipment {self.name!r}>"


class Experiment(TimestampMixin, db.Model):
    """Опыт с водой — наука vs мифы."""

    __tablename__ = "experiments"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    verdict = db.Column(db.String(20), nullable=False)  # 'наука' или 'миф'

    def __repr__(self):
        return f"<Experiment {self.title!r}: {self.verdict}>"


class DeliveryService(TimestampMixin, db.Model):
    """Служба доставки воды."""

    __tablename__ = "delivery_services"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    coverage = db.Column(db.String(255), nullable=True)  # зона доставки
    delivery_time = db.Column(db.String(120), nullable=False)  # сроки, например "1-2 дня"
    price_rub = db.Column(db.Numeric(10, 2), nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    website = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f"<DeliveryService {self.name!r}>"
