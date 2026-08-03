"""Конфигурация приложения. Значения читаются из переменных окружения (.env)."""
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _normalize_db_url(url):
    """Render и некоторые другие хостинги отдают DATABASE_URL со схемой
    postgres://, которую современный SQLAlchemy не принимает — нужен
    postgresql://."""
    if url and url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


class Config:
    """Базовая конфигурация, общая для всех окружений."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    ITEMS_PER_PAGE = int(os.environ.get("ITEMS_PER_PAGE", 9))

    # Пароль для входа в /admin (панель модерации предложенных правок).
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin-change-me")

    # Если true — seed.py всегда стирает и заново заполняет БД из CSV,
    # даже если в ней уже есть данные (например, одобренные через /admin
    # правки). По умолчанию выключено, чтобы не терять такие правки.
    FORCE_RESEED = os.environ.get("FORCE_RESEED", "false").lower() == "true"

    # SMTP для писем подтверждения регистрации. Если MAIL_USERNAME не
    # задан, письма реально не отправляются — вместо этого ссылка
    # подтверждения выводится в лог и на страницу (для локальной
    # разработки и как аварийный запасной вариант).
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "Исток <noreply@istok.example>")

    # Срок жизни ссылки подтверждения email, в секундах (по умолчанию сутки).
    CONFIRM_TOKEN_MAX_AGE = int(os.environ.get("CONFIRM_TOKEN_MAX_AGE", 86400))


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///" + os.path.join(BASE_DIR, "instance", "istok.db")
    )


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get("TEST_DATABASE_URL", "sqlite:///:memory:")
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = _normalize_db_url(os.environ.get("DATABASE_URL"))


config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
