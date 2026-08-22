"""SQLAlchemy-модели проекта «Собутыльник»."""
from datetime import datetime

from app import db


class TimestampMixin:
    """Добавляет created_at/updated_at любой модели."""

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class User(TimestampMixin, db.Model):
    """Зарегистрированный пользователь."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    email_confirmed = db.Column(db.Boolean, nullable=False, default=False)
    confirmed_at = db.Column(db.DateTime, nullable=True)

    # Выбор собеседника (личность) и голоса (Web Speech API браузера,
    # список голосов зависит от устройства — хранится как есть).
    companion_key = db.Column(db.String(50), nullable=True)
    voice_name = db.Column(db.String(255), nullable=True)

    # Индивидуальная блокировка админом ("по одному") — независима от
    # общего рубильника AppSettings.app_enabled ("вся программа").
    is_blocked = db.Column(db.Boolean, nullable=False, default=False)
    blocked_reason = db.Column(db.String(255), nullable=True)

    # Статус оплаты — переключается администратором вручную из карточки
    # пользователя (интеграция с конкретным платёжным провайдером не
    # входит в этот этап — см. README «Что не реализовано»). Определяет,
    # что видит пользователь в чате поддержки и есть ли у него доступ к
    # полноценному общению сверх лимита демо.
    is_paid = db.Column(db.Boolean, nullable=False, default=False)

    # Лимит сообщений ИИ-собеседнику на пользователя — предохранитель от
    # разорения администратора на API. None = использовать
    # AppSettings.default_message_limit. Полностью отключается глобально
    # через AppSettings.limits_enabled («отключить все лимиты по желанию»).
    message_limit = db.Column(db.Integer, nullable=True)
    messages_used = db.Column(db.Integer, nullable=False, default=0)

    conversations = db.relationship(
        "Conversation", backref="user", order_by="Conversation.started_at.desc()",
        cascade="all, delete-orphan",
    )
    support_messages = db.relationship(
        "SupportMessage", backref="user", order_by="SupportMessage.created_at",
        cascade="all, delete-orphan",
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
    def companion(self):
        from app.companions import get_companion

        return get_companion(self.companion_key)

    def effective_limit(self, default_limit):
        return self.message_limit if self.message_limit is not None else default_limit

    def __repr__(self):
        return f"<User {self.email!r}>"


class AppSettings(db.Model):
    """Singleton-строка глобальных настроек (панель администратора).

    Ровно одна запись с id=1 — читается/создаётся через get_settings()
    ниже. Хранит рубильник «вся программа» и общее вкл/выкл лимитов."""

    __tablename__ = "app_settings"

    id = db.Column(db.Integer, primary_key=True)

    # «Полностью заблокировать всю программу» — при False приложение
    # недоступно вообще всем не-администраторам (см. before_request в
    # app/__init__.py). Отдельно от блокировки отдельных пользователей.
    app_enabled = db.Column(db.Boolean, nullable=False, default=True)
    disabled_message = db.Column(
        db.String(500), nullable=True, default="Сервис временно недоступен. Загляните позже."
    )

    # «Отключить все лимиты по желанию» — при False лимиты сообщений
    # (User.message_limit / default_message_limit) не проверяются вообще,
    # даже если у пользователей выставлены конкретные числа.
    limits_enabled = db.Column(db.Boolean, nullable=False, default=True)
    default_message_limit = db.Column(db.Integer, nullable=False, default=60)

    def __repr__(self):
        return f"<AppSettings app_enabled={self.app_enabled} limits_enabled={self.limits_enabled}>"


def get_settings():
    """Возвращает singleton-настройки, создавая запись по умолчанию при первом обращении."""
    from flask import current_app

    settings = db.session.get(AppSettings, 1)
    if settings is None:
        settings = AppSettings(
            id=1, default_message_limit=current_app.config.get("DEFAULT_MESSAGE_LIMIT", 60)
        )
        db.session.add(settings)
        db.session.commit()
    return settings


class Conversation(TimestampMixin, db.Model):
    """Одна сессия «застолья» с ИИ-собеседником."""

    __tablename__ = "conversations"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    companion_key = db.Column(db.String(50), nullable=False)
    started_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    ended_at = db.Column(db.DateTime, nullable=True)

    messages = db.relationship(
        "Message", backref="conversation", order_by="Message.created_at",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Conversation #{self.id} user_id={self.user_id}>"


class Message(db.Model):
    """Одна реплика в диалоге — от пользователя или от собеседника."""

    __tablename__ = "messages"

    SENDER_USER = "user"
    SENDER_COMPANION = "companion"

    KIND_TEXT = "text"
    KIND_TOAST = "toast"
    KIND_JOKE = "joke"
    KIND_MUSIC = "music"

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey("conversations.id"), nullable=False)
    sender = db.Column(db.String(20), nullable=False)
    kind = db.Column(db.String(20), nullable=False, default=KIND_TEXT)
    content = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(500), nullable=True)  # снимок обстановки, если был приложен
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Message #{self.id} sender={self.sender} kind={self.kind}>"


class SupportMessage(TimestampMixin, db.Model):
    """Сообщение в чате техподдержки между пользователем и админом
    (вопросы про оплату/доступ, жалобы, вложенные файлы/фото — раздел
    ТЗ «чат с админом»)."""

    __tablename__ = "support_messages"

    SENDER_USER = "user"
    SENDER_ADMIN = "admin"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    sender = db.Column(db.String(20), nullable=False)
    body = db.Column(db.Text, nullable=True)
    attachment_url = db.Column(db.String(500), nullable=True)
    attachment_name = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    read_by_admin = db.Column(db.Boolean, nullable=False, default=False)
    read_by_user = db.Column(db.Boolean, nullable=False, default=False)

    def __repr__(self):
        return f"<SupportMessage #{self.id} user_id={self.user_id} sender={self.sender}>"
