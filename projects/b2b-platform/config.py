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

    # Письма подтверждения регистрации отправляются через HTTP-API Resend, а
    # не через SMTP — большинство хостингов на бесплатном тарифе блокируют
    # исходящие SMTP-соединения. Если RESEND_API_KEY не задан, письма реально
    # не отправляются — вместо этого ссылка подтверждения выводится в лог и
    # на страницу (для локальной разработки и как аварийный запасной вариант).
    RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER") or "B2B Platform <onboarding@resend.dev>"

    # Срок жизни ссылки подтверждения email, в секундах (по умолчанию сутки).
    CONFIRM_TOKEN_MAX_AGE = int(os.environ.get("CONFIRM_TOKEN_MAX_AGE", 86400))

    # Вход через Google (OAuth 2.0). Если оба значения не заданы, кнопка
    # «Войти через Google» скрывается сама — платформа не притворяется, что
    # эта возможность работает без реальных учётных данных.
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")

    # Загруженные пользователями фото (заказы, объявления барахолки,
    # доказательства в спорах) уходят на ImgBB — Render не хранит файлы на
    # диске между деплоями. Без ключа загрузка фото просто недоступна, форма
    # сохраняется без фото.
    IMGBB_API_KEY = os.environ.get("IMGBB_API_KEY")

    # Telegram-бот (модуль 7). Без токена уведомления идут только in-app.
    TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
    TELEGRAM_BOT_USERNAME = os.environ.get("TELEGRAM_BOT_USERNAME")
    # Секретный сегмент пути вебхука — заменяет отсутствующую у Telegram
    # подпись запроса: /telegram/webhook/<этот_секрет>. Обязателен для
    # включения приёма вебхуков в проде.
    TELEGRAM_WEBHOOK_SECRET = os.environ.get("TELEGRAM_WEBHOOK_SECRET")
    # Нужен только когда send_telegram_notification вызывается вне HTTP-
    # запроса (например, из будущей фоновой задачи) — для формирования
    # абсолютных ссылок в тексте сообщения.
    PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL")

    WTF_CSRF_TIME_LIMIT = None  # токен не должен протухать раньше сессии


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///" + os.path.join(BASE_DIR, "instance", "b2b_platform.db")
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
