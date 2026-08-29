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

    # Письма подтверждения регистрации отправляются через HTTP-API Resend, а
    # не через SMTP — Render блокирует исходящие SMTP-соединения на
    # бесплатном тарифе. Если RESEND_API_KEY не задан, письма реально не
    # отправляются — вместо этого ссылка подтверждения выводится в лог и на
    # страницу (для локальной разработки и как аварийный запасной вариант).
    RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
    # Хостинг может передать переменную пустой строкой, а не отсутствующей —
    # тогда os.environ.get(..., default) не подставит значение по умолчанию,
    # поэтому проверяем и пустую строку. Без верификации своего домена в
    # Resend можно отправлять только с их тестового адреса onboarding@resend.dev.
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER") or "Исток <onboarding@resend.dev>"

    # Срок жизни ссылки подтверждения email, в секундах (по умолчанию сутки).
    CONFIRM_TOKEN_MAX_AGE = int(os.environ.get("CONFIRM_TOKEN_MAX_AGE", 86400))

    # Срок жизни ссылки восстановления пароля, в секундах (по умолчанию час) —
    # короче, чем у подтверждения email, т.к. даёт доступ к самому аккаунту.
    PASSWORD_RESET_TOKEN_MAX_AGE = int(os.environ.get("PASSWORD_RESET_TOKEN_MAX_AGE", 3600))

    # Загруженные пользователями фото уходят на ImgBB (HTTP API) — Render не
    # хранит файлы между деплоями (диск эфемерный), а свой файл-сервер для
    # небольшого личного портала избыточен. Если IMGBB_API_KEY не задан,
    # загрузка фото просто недоступна (поле формы игнорируется).
    IMGBB_API_KEY = os.environ.get("IMGBB_API_KEY")

    # Вход через Google (OAuth 2.0). Если не заданы — кнопка "Войти через
    # Google" на страницах входа/регистрации просто не показывается.
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")

    # Telegram-бот: уведомления о новых личных сообщениях и привязка
    # аккаунта (страница «Сообщения → Telegram»). Без TELEGRAM_BOT_TOKEN
    # бот не отправляет ничего по-настоящему — сайт продолжает работать
    # как раньше, только через личный кабинет. См. .env.example.
    TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
    TELEGRAM_BOT_USERNAME = os.environ.get("TELEGRAM_BOT_USERNAME")
    TELEGRAM_WEBHOOK_SECRET = os.environ.get("TELEGRAM_WEBHOOK_SECRET")
    # Если задан — сообщения в «Администрацию» (Message с recipient=NULL)
    # тоже дублируются в этот чат, т.к. у администрации нет своего user_id.
    ADMIN_TELEGRAM_CHAT_ID = os.environ.get("ADMIN_TELEGRAM_CHAT_ID")


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
