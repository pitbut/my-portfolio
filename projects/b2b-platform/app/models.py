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
