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

    # Провайдер ИИ выбирается по имени — универсальный слой (app/providers/),
    # позволяющий добавить Groq/Gemini/OpenAI как альтернативные адаптеры
    # без переделки маршрутов. На старте поддержан только Anthropic Claude.
    AI_PROVIDER = os.environ.get("AI_PROVIDER", "anthropic")
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
    ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5")

    # Письма подтверждения регистрации отправляются через HTTP-API Resend, а
    # не через SMTP — Render блокирует исходящие SMTP-соединения на
    # бесплатном тарифе. Если RESEND_API_KEY не задан, письма реально не
    # отправляются — вместо этого ссылка подтверждения выводится в лог и на
    # страницу (для локальной разработки и как аварийный запасной вариант).
    RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER") or "Собутыльник <onboarding@resend.dev>"

    # Срок жизни ссылки подтверждения email, в секундах (по умолчанию сутки).
    CONFIRM_TOKEN_MAX_AGE = int(os.environ.get("CONFIRM_TOKEN_MAX_AGE", 86400))

    # Файлы/фото, приложенные в чат поддержки, загружаются на ImgBB (HTTP
    # API) — Render не хранит файлы между деплоями. Если IMGBB_API_KEY не
    # задан, вложение не сохраняется постоянно (сообщение всё равно уходит
    # админу текстом).
    IMGBB_API_KEY = os.environ.get("IMGBB_API_KEY")

    # Сколько реплик даётся гостю (без регистрации) в демо-режиме, прежде чем
    # показать призыв зарегистрироваться — см. app/routes/main.py:demo_reply.
    GUEST_DEMO_TURNS = int(os.environ.get("GUEST_DEMO_TURNS", 4))

    # Лимит сообщений на пользователя в день по умолчанию для НОВЫХ
    # пользователей — чтобы администратор не разорился на API. Реальное
    # включение/выключение лимитов и лимит по каждому пользователю
    # управляются из админ-панели и хранятся в AppSettings/User (см.
    # app/models.py) — эта переменная только задаёт стартовое значение при
    # первом посеве настроек (см. seed.py).
    DEFAULT_MESSAGE_LIMIT = int(os.environ.get("DEFAULT_MESSAGE_LIMIT", 60))

    # Пароль для входа в /admin — единственный администратор, без отдельной
    # роли в таблице users (тот же паттерн, что в istok/ai-tutor/b2b-platform).
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin-change-me")


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or (
        "sqlite:///" + os.path.join(BASE_DIR, "instance", "sobutylnik.db")
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
