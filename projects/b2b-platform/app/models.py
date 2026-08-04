"""SQLAlchemy-модели B2B-платформы изготовителей и ремонтников оборудования.

Схема соответствует ТЗ (см. projects/b2b-equipment-platform-uz) — модуль 1
(пользователи), модуль 3 (профили и техвозможности). Остальные домены
(заказы, барахолка, вакансии) описаны в ТЗ и будут добавлены отдельными
миграциями по мере разработки соответствующих модулей.
"""
from datetime import datetime

from app import db

# --- языки интерфейса и языки пользовательского контента ---
LANGUAGES = ("ru", "uz_latin", "uz_cyrillic")

# --- многие-ко-многим: техвозможности исполнителя <-> услуги / материалы ---
capability_services = db.Table(
    "executor_capability_services",
    db.Column("capability_id", db.Integer, db.ForeignKey("executor_capabilities.id"), primary_key=True),
    db.Column("service_category_id", db.Integer, db.ForeignKey("service_categories.id"), primary_key=True),
)

capability_materials = db.Table(
    "executor_capability_materials",
    db.Column("capability_id", db.Integer, db.ForeignKey("executor_capabilities.id"), primary_key=True),
    db.Column("material_id", db.Integer, db.ForeignKey("materials.id"), primary_key=True),
)


class TimestampMixin:
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class User(TimestampMixin, db.Model):
    """Базовая учётная запись — общая и для заказчика, и для исполнителя."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=True)  # NULL, если вход только через Google
    google_sub = db.Column(db.String(255), unique=True, nullable=True, index=True)
    phone = db.Column(db.String(50), nullable=True)

    # NULL сразу после входа через Google, пока пользователь не выбрал роль
    # (модуль 1: «если это первый вход — короткий шаг выбора роли»).
    role = db.Column(db.String(20), nullable=True)  # customer | executor | admin

    preferred_language = db.Column(db.String(20), nullable=False, default="ru")
    email_confirmed = db.Column(db.Boolean, nullable=False, default=False)
    confirmed_at = db.Column(db.DateTime, nullable=True)
    is_blocked = db.Column(db.Boolean, nullable=False, default=False)
    last_login_at = db.Column(db.DateTime, nullable=True)

    customer_profile = db.relationship(
        "CustomerProfile", backref="user", uselist=False, cascade="all, delete-orphan"
    )
    executor_profile = db.relationship(
        "ExecutorProfile", backref="user", uselist=False, cascade="all, delete-orphan"
    )

    # --- интерфейс, ожидаемый Flask-Login ---
    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return not self.is_blocked

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

    @property
    def active_profile(self):
        if self.role == "customer":
            return self.customer_profile
        if self.role == "executor":
            return self.executor_profile
        return None

    @property
    def profile_complete(self):
        profile = self.active_profile
        return bool(profile and profile.is_complete)

    def __repr__(self):
        return f"<User {self.email!r} role={self.role!r}>"


class Region(db.Model):
    """Область/регион Узбекистана (справочник)."""

    __tablename__ = "regions"

    id = db.Column(db.Integer, primary_key=True)
    name_ru = db.Column(db.String(120), nullable=False)
    name_uz_latin = db.Column(db.String(120), nullable=False)
    name_uz_cyrillic = db.Column(db.String(120), nullable=False)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)

    cities = db.relationship("City", backref="region", order_by="City.name_ru")

    def name(self, lang):
        return getattr(self, f"name_{lang}", self.name_ru)

    def __repr__(self):
        return f"<Region {self.name_ru!r}>"


class City(db.Model):
    """Город внутри региона (справочник)."""

    __tablename__ = "cities"

    id = db.Column(db.Integer, primary_key=True)
    region_id = db.Column(db.Integer, db.ForeignKey("regions.id"), nullable=False)
    name_ru = db.Column(db.String(120), nullable=False)
    name_uz_latin = db.Column(db.String(120), nullable=False)
    name_uz_cyrillic = db.Column(db.String(120), nullable=False)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)

    def name(self, lang):
        return getattr(self, f"name_{lang}", self.name_ru)

    def __repr__(self):
        return f"<City {self.name_ru!r}>"


class EquipmentType(db.Model):
    """Справочник видов станков/оборудования (станочный парк)."""

    __tablename__ = "equipment_types"

    id = db.Column(db.Integer, primary_key=True)
    name_ru = db.Column(db.String(160), nullable=False)
    name_uz_latin = db.Column(db.String(160), nullable=False)
    name_uz_cyrillic = db.Column(db.String(160), nullable=False)

    def name(self, lang):
        return getattr(self, f"name_{lang}", self.name_ru)

    def __repr__(self):
        return f"<EquipmentType {self.name_ru!r}>"


class ServiceCategory(db.Model):
    """Справочник категорий услуг (что умеет исполнитель / что нужно заказчику)."""

    __tablename__ = "service_categories"

    id = db.Column(db.Integer, primary_key=True)
    name_ru = db.Column(db.String(160), nullable=False)
    name_uz_latin = db.Column(db.String(160), nullable=False)
    name_uz_cyrillic = db.Column(db.String(160), nullable=False)

    def name(self, lang):
        return getattr(self, f"name_{lang}", self.name_ru)

    def __repr__(self):
        return f"<ServiceCategory {self.name_ru!r}>"


class Material(db.Model):
    """Справочник материалов, с которыми работает исполнитель."""

    __tablename__ = "materials"

    id = db.Column(db.Integer, primary_key=True)
    name_ru = db.Column(db.String(160), nullable=False)
    name_uz_latin = db.Column(db.String(160), nullable=False)
    name_uz_cyrillic = db.Column(db.String(160), nullable=False)

    def name(self, lang):
        return getattr(self, f"name_{lang}", self.name_ru)

    def __repr__(self):
        return f"<Material {self.name_ru!r}>"


class CustomerProfile(TimestampMixin, db.Model):
    """Карточка заказчика — заполняется самим заказчиком (модуль 3)."""

    __tablename__ = "customer_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)

    kind = db.Column(db.String(20), nullable=True)  # individual | company
    display_name = db.Column(db.String(255), nullable=True)
    stir_inn = db.Column(db.String(50), nullable=True)

    region_id = db.Column(db.Integer, db.ForeignKey("regions.id"), nullable=True)
    city_id = db.Column(db.Integer, db.ForeignKey("cities.id"), nullable=True)
    address_text = db.Column(db.String(500), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)

    rating_avg = db.Column(db.Numeric(3, 2), nullable=True)
    reviews_count = db.Column(db.Integer, nullable=False, default=0)

    region = db.relationship("Region")
    city = db.relationship("City")

    @property
    def is_complete(self):
        """Минимум, необходимый для публикации заказа (модуль 2)."""
        return bool(self.kind and self.display_name and self.region_id and self.address_text)

    def __repr__(self):
        return f"<CustomerProfile user_id={self.user_id}>"


class ExecutorProfile(TimestampMixin, db.Model):
    """Карточка исполнителя — заполняется самим исполнителем (модуль 3)."""

    __tablename__ = "executor_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)

    org_type = db.Column(db.String(20), nullable=True)  # master | tsekh | zavod
    display_name = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=True)
    stir_inn = db.Column(db.String(50), nullable=True)

    region_id = db.Column(db.Integer, db.ForeignKey("regions.id"), nullable=True)
    city_id = db.Column(db.Integer, db.ForeignKey("cities.id"), nullable=True)
    address_text = db.Column(db.String(500), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    service_radius_km = db.Column(db.Integer, nullable=True, default=50)

    is_verified = db.Column(db.Boolean, nullable=False, default=False)
    rating_avg = db.Column(db.Numeric(3, 2), nullable=True)
    reviews_count = db.Column(db.Integer, nullable=False, default=0)

    region = db.relationship("Region")
    city = db.relationship("City")
    equipment = db.relationship(
        "ExecutorEquipment", backref="executor", cascade="all, delete-orphan",
        order_by="ExecutorEquipment.id",
    )
    capability = db.relationship(
        "ExecutorCapability", backref="executor", uselist=False, cascade="all, delete-orphan"
    )

    @property
    def is_complete(self):
        """Профиль «опубликован» и участвует в матчинге только при заполнении
        обязательного минимума: организация, локация, хотя бы одна единица
        станочного парка и заполненные габариты/услуги (модуль 3)."""
        return bool(
            self.org_type
            and self.display_name
            and self.region_id
            and self.address_text
            and self.equipment
            and self.capability
            and self.capability.service_categories
        )

    def __repr__(self):
        return f"<ExecutorProfile user_id={self.user_id}>"


class ExecutorEquipment(db.Model):
    """Единица станочного парка исполнителя (1:N)."""

    __tablename__ = "executor_equipment"

    id = db.Column(db.Integer, primary_key=True)
    executor_id = db.Column(db.Integer, db.ForeignKey("executor_profiles.id"), nullable=False)
    equipment_type_id = db.Column(db.Integer, db.ForeignKey("equipment_types.id"), nullable=False)
    model_name = db.Column(db.String(255), nullable=True)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    notes = db.Column(db.Text, nullable=True)

    equipment_type = db.relationship("EquipmentType")

    def __repr__(self):
        return f"<ExecutorEquipment executor_id={self.executor_id} type_id={self.equipment_type_id}>"


class ExecutorCapability(db.Model):
    """Допустимые габариты, вес и перечень услуг/материалов исполнителя."""

    __tablename__ = "executor_capabilities"

    id = db.Column(db.Integer, primary_key=True)
    executor_id = db.Column(db.Integer, db.ForeignKey("executor_profiles.id"), unique=True, nullable=False)

    max_length_mm = db.Column(db.Integer, nullable=True)
    max_diameter_mm = db.Column(db.Integer, nullable=True)
    max_width_mm = db.Column(db.Integer, nullable=True)
    max_height_mm = db.Column(db.Integer, nullable=True)
    max_weight_kg = db.Column(db.Numeric(10, 2), nullable=True)

    service_categories = db.relationship("ServiceCategory", secondary=capability_services)
    materials = db.relationship("Material", secondary=capability_materials)

    def __repr__(self):
        return f"<ExecutorCapability executor_id={self.executor_id}>"


# --- модуль 2: заказы, медиа, автоподбор, аукцион ---

ORDER_OPEN_STATUSES = ("published",)
ORDER_STATUSES = (
    "draft", "published", "assigned", "in_progress", "completed", "disputed", "cancelled",
)


class Order(TimestampMixin, db.Model):
    """Заявка заказчика на изготовление или ремонт."""

    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customer_profiles.id"), nullable=False)

    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    content_language = db.Column(db.String(20), nullable=False, default="ru")
    order_type = db.Column(db.String(20), nullable=False)  # manufacturing | repair
    service_category_id = db.Column(db.Integer, db.ForeignKey("service_categories.id"), nullable=False)
    material_id = db.Column(db.Integer, db.ForeignKey("materials.id"), nullable=True)

    dimensions_length_mm = db.Column(db.Integer, nullable=True)
    dimensions_diameter_mm = db.Column(db.Integer, nullable=True)
    dimensions_width_mm = db.Column(db.Integer, nullable=True)
    dimensions_height_mm = db.Column(db.Integer, nullable=True)
    weight_kg = db.Column(db.Numeric(10, 2), nullable=True)

    budget_min = db.Column(db.Numeric(12, 2), nullable=True)
    budget_max = db.Column(db.Numeric(12, 2), nullable=True)
    deadline_date = db.Column(db.Date, nullable=True)

    region_id = db.Column(db.Integer, db.ForeignKey("regions.id"), nullable=False)
    city_id = db.Column(db.Integer, db.ForeignKey("cities.id"), nullable=True)
    address_text = db.Column(db.String(500), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)

    auction_deadline_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="published")

    customer = db.relationship("CustomerProfile", backref="orders")
    service_category = db.relationship("ServiceCategory")
    material = db.relationship("Material")
    region = db.relationship("Region")
    city = db.relationship("City")
    media = db.relationship("OrderMedia", backref="order", cascade="all, delete-orphan", order_by="OrderMedia.sort_order")
    matches = db.relationship("OrderMatch", backref="order", cascade="all, delete-orphan")
    bids = db.relationship("Bid", backref="order", cascade="all, delete-orphan", order_by="Bid.price")
    assignment = db.relationship("OrderAssignment", backref="order", uselist=False, cascade="all, delete-orphan")

    @property
    def is_open_for_bids(self):
        if self.status != "published":
            return False
        if self.auction_deadline_at and self.auction_deadline_at < datetime.utcnow():
            return False
        return True

    def __repr__(self):
        return f"<Order {self.id} {self.title!r} status={self.status!r}>"


class OrderMedia(db.Model):
    """Фото/чертежи/видео/документы, приложенные к заявке."""

    __tablename__ = "order_media"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    media_type = db.Column(db.String(20), nullable=False)  # photo | drawing | video | document
    file_url = db.Column(db.String(1000), nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    def __repr__(self):
        return f"<OrderMedia order_id={self.order_id} type={self.media_type!r}>"


class OrderMatch(db.Model):
    """Результат автоподбора: кандидат-исполнитель под конкретный заказ."""

    __tablename__ = "order_matches"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    executor_id = db.Column(db.Integer, db.ForeignKey("executor_profiles.id"), nullable=False)
    match_score = db.Column(db.Numeric(6, 2), nullable=False, default=0)
    distance_km = db.Column(db.Numeric(8, 2), nullable=True)
    notified_at = db.Column(db.DateTime, nullable=True)
    viewed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    executor = db.relationship("ExecutorProfile")

    __table_args__ = (db.UniqueConstraint("order_id", "executor_id", name="uq_order_match"),)

    def __repr__(self):
        return f"<OrderMatch order_id={self.order_id} executor_id={self.executor_id} score={self.match_score}>"


class Bid(TimestampMixin, db.Model):
    """Ставка исполнителя в аукционе по заказу."""

    __tablename__ = "bids"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    executor_id = db.Column(db.Integer, db.ForeignKey("executor_profiles.id"), nullable=False)
    price = db.Column(db.Numeric(12, 2), nullable=False)
    currency = db.Column(db.String(10), nullable=False, default="UZS")
    lead_time_days = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="active")  # active | withdrawn | accepted | rejected

    executor = db.relationship("ExecutorProfile")

    __table_args__ = (db.UniqueConstraint("order_id", "executor_id", name="uq_order_bid_per_executor"),)

    def __repr__(self):
        return f"<Bid order_id={self.order_id} executor_id={self.executor_id} price={self.price}>"


class OrderAssignment(db.Model):
    """Назначение победителя аукциона по заказу (1:1)."""

    __tablename__ = "order_assignments"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), unique=True, nullable=False)
    bid_id = db.Column(db.Integer, db.ForeignKey("bids.id"), nullable=False)
    agreed_price = db.Column(db.Numeric(12, 2), nullable=False)
    agreed_deadline = db.Column(db.Date, nullable=True)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    completed_at = db.Column(db.DateTime, nullable=True)

    bid = db.relationship("Bid")

    def __repr__(self):
        return f"<OrderAssignment order_id={self.order_id} bid_id={self.bid_id}>"


class OrderStatusHistory(db.Model):
    """Журнал смены статусов заказа (аудит)."""

    __tablename__ = "order_status_history"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    from_status = db.Column(db.String(20), nullable=True)
    to_status = db.Column(db.String(20), nullable=False)
    changed_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<OrderStatusHistory order_id={self.order_id} -> {self.to_status!r}>"


def record_status_change(order, to_status, user=None):
    """Общий помощник: меняет статус заказа и пишет запись в журнал."""
    from_status = order.status
    order.status = to_status
    db.session.add(OrderStatusHistory(order_id=order.id, from_status=from_status, to_status=to_status,
                                       changed_by_user_id=user.id if user else None))


# --- единая нотификационная шина (используется модулями 2, 7, 8, 9) ---

NOTIFICATION_TYPES = (
    "new_order_match", "outbid", "bid_accepted", "bid_rejected", "order_completed", "dispute_update",
    "subscription_expiring", "review_received", "listing_response", "vacancy_response", "resume_invite",
)


class Notification(db.Model):
    """Запись о событии, о котором пользователь должен быть уведомлён.

    Общая точка входа для всех модулей (заказы/барахолка/вакансии) — модуль 7
    (Telegram-бот) просто добавляет ещё один канал доставки поверх той же
    таблицы, ничего не меняя в остальных модулях."""

    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    type = db.Column(db.String(30), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text, nullable=True)
    url = db.Column(db.String(500), nullable=True)
    telegram_sent = db.Column(db.Boolean, nullable=False, default=False)
    read_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    user = db.relationship("User")

    def __repr__(self):
        return f"<Notification user_id={self.user_id} type={self.type!r}>"


# --- модуль 5: отзывы и рейтинги ---

class Review(TimestampMixin, db.Model):
    """Двусторонний отзыв по завершённому заказу — публикуется только после
    того, как своё мнение оставили обе стороны (защита от «жду его оценку,
    чтобы ответить тем же», см. ТЗ)."""

    __tablename__ = "reviews"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    target_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    direction = db.Column(db.String(30), nullable=False)  # customer_to_executor | executor_to_customer
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=True)
    is_published = db.Column(db.Boolean, nullable=False, default=False)

    order = db.relationship("Order")
    author = db.relationship("User", foreign_keys=[author_id])
    target = db.relationship("User", foreign_keys=[target_id])

    __table_args__ = (db.UniqueConstraint("order_id", "author_id", name="uq_review_per_order_author"),)

    def __repr__(self):
        return f"<Review order_id={self.order_id} author_id={self.author_id} rating={self.rating}>"


# --- модуль 6: арбитраж и медиация ---

DISPUTE_STATUSES = (
    "open", "evidence_collection", "in_review",
    "resolved_customer", "resolved_executor", "resolved_partial", "closed",
)
DISPUTE_REASON_CATEGORIES = ("defect", "delay", "quality", "price_dispute", "other")


class Dispute(TimestampMixin, db.Model):
    """Спор по заказу (1:1) — брак, задержка, претензия по качеству и т.п."""

    __tablename__ = "disputes"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), unique=True, nullable=False)
    opened_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    reason_category = db.Column(db.String(30), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(30), nullable=False, default="open")
    assigned_admin_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    resolution_text = db.Column(db.Text, nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)

    order = db.relationship("Order", backref=db.backref("dispute", uselist=False))
    opened_by = db.relationship("User", foreign_keys=[opened_by_user_id])
    assigned_admin = db.relationship("User", foreign_keys=[assigned_admin_id])
    evidence = db.relationship("DisputeEvidence", backref="dispute", cascade="all, delete-orphan", order_by="DisputeEvidence.created_at")
    messages = db.relationship("DisputeMessage", backref="dispute", cascade="all, delete-orphan", order_by="DisputeMessage.created_at")

    def __repr__(self):
        return f"<Dispute order_id={self.order_id} status={self.status!r}>"


class DisputeEvidence(db.Model):
    """Фото/видео/документ-доказательство от одной из сторон."""

    __tablename__ = "dispute_evidence"

    id = db.Column(db.Integer, primary_key=True)
    dispute_id = db.Column(db.Integer, db.ForeignKey("disputes.id"), nullable=False)
    uploaded_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    media_type = db.Column(db.String(20), nullable=False)  # photo | video | document
    file_url = db.Column(db.String(1000), nullable=False)
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    uploaded_by = db.relationship("User")

    def __repr__(self):
        return f"<DisputeEvidence dispute_id={self.dispute_id}>"


class DisputeMessage(db.Model):
    """Переписка сторон и администратора внутри спора."""

    __tablename__ = "dispute_messages"

    id = db.Column(db.Integer, primary_key=True)
    dispute_id = db.Column(db.Integer, db.ForeignKey("disputes.id"), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    text = db.Column(db.Text, nullable=False)
    is_internal_admin_note = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    sender = db.relationship("User")

    def __repr__(self):
        return f"<DisputeMessage dispute_id={self.dispute_id}>"


# --- модуль 8: барахолка станков и инструмента ---

class ListingCategory(db.Model):
    """Справочник категорий объявлений (станки, инструмент, запчасти...)."""

    __tablename__ = "listing_categories"

    id = db.Column(db.Integer, primary_key=True)
    name_ru = db.Column(db.String(160), nullable=False)
    name_uz_latin = db.Column(db.String(160), nullable=False)
    name_uz_cyrillic = db.Column(db.String(160), nullable=False)

    def name(self, lang):
        return getattr(self, f"name_{lang}", self.name_ru)

    def __repr__(self):
        return f"<ListingCategory {self.name_ru!r}>"


class Listing(TimestampMixin, db.Model):
    """Объявление о продаже/покупке станка, инструмента, запчастей."""

    __tablename__ = "listings"

    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    listing_intent = db.Column(db.String(10), nullable=False)  # sell | buy
    category_id = db.Column(db.Integer, db.ForeignKey("listing_categories.id"), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    content_language = db.Column(db.String(20), nullable=False, default="ru")
    condition = db.Column(db.String(20), nullable=True)  # new | used | for_parts (только для sell)
    price = db.Column(db.Numeric(12, 2), nullable=True)
    currency = db.Column(db.String(10), nullable=False, default="UZS")
    price_negotiable = db.Column(db.Boolean, nullable=False, default=False)
    region_id = db.Column(db.Integer, db.ForeignKey("regions.id"), nullable=False)
    city_id = db.Column(db.Integer, db.ForeignKey("cities.id"), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="active")  # active | reserved | closed | archived

    author = db.relationship("User")
    category = db.relationship("ListingCategory")
    region = db.relationship("Region")
    city = db.relationship("City")
    media = db.relationship("ListingMedia", backref="listing", cascade="all, delete-orphan", order_by="ListingMedia.sort_order")
    responses = db.relationship("ListingResponse", backref="listing", cascade="all, delete-orphan", order_by="ListingResponse.created_at")

    def __repr__(self):
        return f"<Listing {self.id} {self.title!r} {self.listing_intent}>"


class ListingMedia(db.Model):
    __tablename__ = "listing_media"

    id = db.Column(db.Integer, primary_key=True)
    listing_id = db.Column(db.Integer, db.ForeignKey("listings.id"), nullable=False)
    media_type = db.Column(db.String(20), nullable=False)  # photo | video
    file_url = db.Column(db.String(1000), nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    def __repr__(self):
        return f"<ListingMedia listing_id={self.listing_id}>"


class ListingResponse(db.Model):
    """Отклик на объявление — уведомляет автора через общую шину (модуль 7)."""

    __tablename__ = "listing_responses"

    id = db.Column(db.Integer, primary_key=True)
    listing_id = db.Column(db.Integer, db.ForeignKey("listings.id"), nullable=False)
    from_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    message = db.Column(db.Text, nullable=True)
    offered_price = db.Column(db.Numeric(12, 2), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    from_user = db.relationship("User")

    def __repr__(self):
        return f"<ListingResponse listing_id={self.listing_id} from={self.from_user_id}>"


# --- модуль 9: вакансии и резюме (найм персонала) ---

class ProfessionCategory(db.Model):
    """Справочник профессий (токарь, фрезеровщик, сварщик...). Отдельно от
    service_categories (модуль 2): там — умение организации, здесь — умение
    человека, хотя списки местами пересекаются."""

    __tablename__ = "profession_categories"

    id = db.Column(db.Integer, primary_key=True)
    name_ru = db.Column(db.String(160), nullable=False)
    name_uz_latin = db.Column(db.String(160), nullable=False)
    name_uz_cyrillic = db.Column(db.String(160), nullable=False)

    def name(self, lang):
        return getattr(self, f"name_{lang}", self.name_ru)

    def __repr__(self):
        return f"<ProfessionCategory {self.name_ru!r}>"


class Vacancy(TimestampMixin, db.Model):
    """Вакансия от работодателя — любой зарегистрированный пользователь
    (не обязательно executor: заказчик тоже может нанимать персонал)."""

    __tablename__ = "vacancies"

    id = db.Column(db.Integer, primary_key=True)
    employer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    profession_category_id = db.Column(db.Integer, db.ForeignKey("profession_categories.id"), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    employment_type = db.Column(db.String(20), nullable=False)  # full_time | part_time | shift | contract
    salary_min = db.Column(db.Numeric(12, 2), nullable=True)
    salary_max = db.Column(db.Numeric(12, 2), nullable=True)
    currency = db.Column(db.String(10), nullable=False, default="UZS")
    region_id = db.Column(db.Integer, db.ForeignKey("regions.id"), nullable=False)
    city_id = db.Column(db.Integer, db.ForeignKey("cities.id"), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="active")  # active | closed | archived

    employer = db.relationship("User")
    profession_category = db.relationship("ProfessionCategory")
    region = db.relationship("Region")
    city = db.relationship("City")

    def __repr__(self):
        return f"<Vacancy {self.id} {self.title!r}>"


class Resume(TimestampMixin, db.Model):
    """Резюме соискателя («ищу работу») — тоже доступно любому пользователю."""

    __tablename__ = "resumes"

    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    profession_category_id = db.Column(db.Integer, db.ForeignKey("profession_categories.id"), nullable=False)
    experience_years = db.Column(db.Integer, nullable=True)
    about = db.Column(db.Text, nullable=False)
    expected_salary = db.Column(db.Numeric(12, 2), nullable=True)
    region_id = db.Column(db.Integer, db.ForeignKey("regions.id"), nullable=False)
    city_id = db.Column(db.Integer, db.ForeignKey("cities.id"), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="active")  # active | hidden

    candidate = db.relationship("User")
    profession_category = db.relationship("ProfessionCategory")
    region = db.relationship("Region")
    city = db.relationship("City")

    def __repr__(self):
        return f"<Resume {self.id} candidate_id={self.candidate_id}>"


class JobResponse(db.Model):
    """Отклик в любую сторону: соискатель откликается на вакансию
    (candidate_to_employer) либо работодатель приглашает по резюме
    (employer_to_candidate). Ровно одно из vacancy_id/resume_id заполнено."""

    __tablename__ = "job_responses"

    id = db.Column(db.Integer, primary_key=True)
    vacancy_id = db.Column(db.Integer, db.ForeignKey("vacancies.id"), nullable=True)
    resume_id = db.Column(db.Integer, db.ForeignKey("resumes.id"), nullable=True)
    from_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    to_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    direction = db.Column(db.String(30), nullable=False)  # candidate_to_employer | employer_to_candidate
    message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    vacancy = db.relationship("Vacancy")
    resume = db.relationship("Resume")
    from_user = db.relationship("User", foreign_keys=[from_user_id])
    to_user = db.relationship("User", foreign_keys=[to_user_id])

    __table_args__ = (
        db.CheckConstraint(
            "(vacancy_id IS NOT NULL AND resume_id IS NULL) OR (vacancy_id IS NULL AND resume_id IS NOT NULL)",
            name="ck_job_response_target",
        ),
    )

    def __repr__(self):
        return f"<JobResponse {self.direction} from={self.from_user_id} to={self.to_user_id}>"
