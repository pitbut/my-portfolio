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


class Book(TimestampMixin, SlugMixin, db.Model):
    """Книга о воде — раздел «Библиотека»."""

    __tablename__ = "books"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    author = db.Column(db.String(255), nullable=False)
    year = db.Column(db.Integer, nullable=True)
    genre = db.Column(db.String(120), nullable=True)
    description = db.Column(db.Text, nullable=False)
    cover_url = db.Column(db.String(500), nullable=True)
    verified = db.Column(db.Boolean, nullable=False, default=True)
    added_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    added_by = db.relationship("User")

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
    verified = db.Column(db.Boolean, nullable=False, default=True)
    added_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    added_by = db.relationship("User")

    def __repr__(self):
        return f"<Article {self.title!r}>"


class WaterBrand(TimestampMixin, SlugMixin, db.Model):
    """Марка питьевой воды — раздел «Каталог цен»."""

    __tablename__ = "water_brands"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    water_type = db.Column(db.String(120), nullable=False)  # питьевая/минеральная/родниковая...
    mineralization_mg_l = db.Column(db.Integer, nullable=True)  # мг/л
    volume_l = db.Column(db.Numeric(5, 2), nullable=False)
    # Цена хранится в собственной валюте страны происхождения (см. currency),
    # а не всегда в рублях — так её можно показывать в естественных для
    # покупателя единицах вместо пересчёта по курсу.
    price = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(8), nullable=False, default="RUB")
    country = db.Column(db.String(120), nullable=True, index=True)
    origin = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=True)
    verified = db.Column(db.Boolean, nullable=False, default=True)
    added_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    added_by = db.relationship("User")

    CURRENCY_SYMBOLS = {
        "RUB": "₽", "UZS": "сум", "KZT": "₸", "GEL": "₾",
        "AMD": "֏", "BYN": "Br", "MDL": "L", "EUR": "€",
    }

    @property
    def currency_symbol(self):
        return self.CURRENCY_SYMBOLS.get(self.currency, self.currency)

    def __repr__(self):
        return f"<WaterBrand {self.name!r}>"


class User(TimestampMixin, db.Model):
    """Зарегистрированный пользователь — может добавлять точки продажи."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    email_confirmed = db.Column(db.Boolean, nullable=False, default=False)
    confirmed_at = db.Column(db.DateTime, nullable=True)

    # --- интерфейс, ожидаемый Flask-Login ---
    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

    def __repr__(self):
        return f"<User {self.email!r}>"


class Supplier(TimestampMixin, db.Model):
    """Точка продажи/оптовый поставщик конкретной марки воды."""

    __tablename__ = "suppliers"

    id = db.Column(db.Integer, primary_key=True)
    water_brand_id = db.Column(db.Integer, db.ForeignKey("water_brands.id"), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    supplier_type = db.Column(db.String(50), nullable=True)  # опт / розница
    address = db.Column(db.String(500), nullable=False)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    website = db.Column(db.String(255), nullable=True)
    image_url = db.Column(db.String(500), nullable=True)
    verified = db.Column(db.Boolean, nullable=False, default=False)
    added_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    water_brand = db.relationship("WaterBrand", backref="suppliers")
    added_by = db.relationship("User")

    def __repr__(self):
        return f"<Supplier {self.name!r} for water_brand_id={self.water_brand_id}>"


class ContactMessage(TimestampMixin, db.Model):
    """Сообщение, отправленное через контактную форму."""

    __tablename__ = "contact_messages"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=True)
    email = db.Column(db.String(255), nullable=True)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, nullable=False, default=False)

    def __repr__(self):
        return f"<ContactMessage #{self.id} from {self.email!r}>"


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
    verified = db.Column(db.Boolean, nullable=False, default=True)
    added_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    added_by = db.relationship("User")

    def __repr__(self):
        return f"<SacredSource {self.name!r} ({self.country})>"


class Equipment(TimestampMixin, SlugMixin, db.Model):
    """Оборудование для воды — фильтры/кулеры/счётчики."""

    __tablename__ = "equipment"

    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(120), nullable=False)  # фильтр/кулер/счётчик
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price_rub = db.Column(db.Numeric(10, 2), nullable=True)
    manufacturer = db.Column(db.String(255), nullable=True)
    image_url = db.Column(db.String(500), nullable=True)
    verified = db.Column(db.Boolean, nullable=False, default=False)
    added_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    added_by = db.relationship("User")

    def __repr__(self):
        return f"<Equipment {self.name!r}>"


class Experiment(TimestampMixin, SlugMixin, db.Model):
    """Опыт с водой — наука vs мифы."""

    __tablename__ = "experiments"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    verdict = db.Column(db.String(20), nullable=False)  # 'наука' или 'миф'
    verified = db.Column(db.Boolean, nullable=False, default=True)
    added_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    added_by = db.relationship("User")

    def __repr__(self):
        return f"<Experiment {self.title!r}: {self.verdict}>"


class EditSuggestion(TimestampMixin, db.Model):
    """Правка источника, предложенная посетителем сайта и ждущая модерации."""

    __tablename__ = "edit_suggestions"

    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"

    FIELD_LABELS = {
        "belief": "Во что верят",
        "allowed": "Что можно",
        "forbidden": "Что нельзя",
        "description": "Описание",
        "comment": "Комментарий редакции",
        "image_url": "Фото",
    }

    id = db.Column(db.Integer, primary_key=True)
    source_id = db.Column(db.Integer, db.ForeignKey("sacred_sources.id"), nullable=False)
    field_name = db.Column(db.String(50), nullable=False)  # ключ из FIELD_LABELS
    proposed_value = db.Column(db.Text, nullable=False)
    message = db.Column(db.Text, nullable=True)  # необязательная пояснительная записка
    submitter_name = db.Column(db.String(120), nullable=True)
    status = db.Column(db.String(20), nullable=False, default=STATUS_PENDING)
    reviewed_at = db.Column(db.DateTime, nullable=True)

    source = db.relationship("SacredSource", backref="suggestions")

    def field_label(self):
        return self.FIELD_LABELS.get(self.field_name, self.field_name)

    def __repr__(self):
        return f"<EditSuggestion #{self.id} {self.field_name} for source_id={self.source_id} ({self.status})>"


class DeliveryService(TimestampMixin, SlugMixin, db.Model):
    """Служба доставки воды."""

    __tablename__ = "delivery_services"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    coverage = db.Column(db.String(255), nullable=True)  # зона доставки
    delivery_time = db.Column(db.String(120), nullable=False)  # сроки, например "1-2 дня"
    price_rub = db.Column(db.Numeric(10, 2), nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    website = db.Column(db.String(255), nullable=True)
    verified = db.Column(db.Boolean, nullable=False, default=True)
    added_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    added_by = db.relationship("User")

    def __repr__(self):
        return f"<DeliveryService {self.name!r}>"


class Banner(TimestampMixin, db.Model):
    """Рекламный баннер в одном из 3 слотов на главной странице.

    "Универсальный" — один и тот же слот может содержать видео, картинку/гиф
    или просто текст, в зависимости от banner_type; лишние для выбранного
    типа поля просто не используются."""

    __tablename__ = "banners"

    BANNER_TYPES = ("video", "image", "text")

    id = db.Column(db.Integer, primary_key=True)
    slot = db.Column(db.Integer, unique=True, nullable=False)  # 1, 2 или 3
    banner_type = db.Column(db.String(20), nullable=False, default="text")
    title = db.Column(db.String(255), nullable=True)
    content_url = db.Column(db.String(500), nullable=True)  # ссылка на видео/картинку
    text_content = db.Column(db.Text, nullable=True)  # текст для banner_type="text"
    link_url = db.Column(db.String(500), nullable=True)  # необязательная ссылка при клике

    def __repr__(self):
        return f"<Banner slot={self.slot} type={self.banner_type!r}>"


class Review(TimestampMixin, db.Model):
    """Отзыв с оценкой на любой раздел сайта (источник, марка воды,
    оборудование, книга, статья, опыт, служба доставки).

    target_type/target_id вместо отдельной таблицы на каждый раздел — чтобы
    добавлять отзывы к новым разделам без новых таблиц и роутов."""

    __tablename__ = "reviews"

    TARGET_TYPES = (
        "sacred_source",
        "water_brand",
        "equipment",
        "book",
        "article",
        "experiment",
        "delivery_service",
    )

    id = db.Column(db.Integer, primary_key=True)
    target_type = db.Column(db.String(50), nullable=False, index=True)
    target_id = db.Column(db.Integer, nullable=False, index=True)
    author_name = db.Column(db.String(120), nullable=True)
    rating = db.Column(db.Integer, nullable=False)  # 1-5
    body = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(500), nullable=True)

    def __repr__(self):
        return f"<Review #{self.id} {self.target_type}:{self.target_id} rating={self.rating}>"
