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

    # Единый ключ мультимодального ИИ-API (текст + изображения), которым
    # закрывается весь интеллектуальный функционал модуля: объяснение темы,
    # генерация заданий, проверка решений по фото — см. ai_client.py.
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
    ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5")

    # Письма подтверждения регистрации отправляются через HTTP-API Resend, а
    # не через SMTP — Render блокирует исходящие SMTP-соединения на
    # бесплатном тарифе. Если RESEND_API_KEY не задан, письма реально не
    # отправляются — вместо этого ссылка подтверждения выводится в лог и на
    # страницу (для локальной разработки и как аварийный запасной вариант).
    RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER") or "ИИ-репетитор <onboarding@resend.dev>"

    # Срок жизни ссылки подтверждения email, в секундах (по умолчанию сутки).
    CONFIRM_TOKEN_MAX_AGE = int(os.environ.get("CONFIRM_TOKEN_MAX_AGE", 86400))

    # Фото решений загружаются на ImgBB (HTTP API) — Render не хранит файлы
    # между деплоями (диск эфемерный). Если IMGBB_API_KEY не задан, фото не
    # сохраняется постоянно, но всё равно один раз анализируется ИИ (модуль
    # проверки решений работает независимо от наличия постоянного хранилища).
    IMGBB_API_KEY = os.environ.get("IMGBB_API_KEY")

    # Минимальный отступ до следующего занятия, в часах (раздел 4.2 ТЗ).
    NEXT_LESSON_MIN_OFFSET_HOURS = int(os.environ.get("NEXT_LESSON_MIN_OFFSET_HOURS", 3))

    # Минимум практических заданий за занятие (раздел 4.2 ТЗ).
    MIN_TASKS_PER_LESSON = int(os.environ.get("MIN_TASKS_PER_LESSON", 3))

    # Имя дефолтного аватара — используется, пока ученик не выбрал свой
    # аватар на онбординге (см. app/avatars.py).
    DEFAULT_AVATAR_NAME = os.environ.get("DEFAULT_AVATAR_NAME", "Алекс")

    # Пароль для входа в /admin — панель управления предметами/классами/
    # программами и просмотра прогресса учеников (раздел 9.3 ТЗ). Тот же
    # паттерн, что в istok/b2b-platform: один пароль на сессию, без
    # отдельной роли в таблице users.
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin-change-me")


class DevelopmentConfig(Config):
    DEBUG = True
    # .env может передать DATABASE_URL пустой строкой, а не отсутствующей
    # переменной — тогда os.environ.get(..., default) не подставит значение
    # по умолчанию, поэтому проверяем и пустую строку.
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or (
        "sqlite:///" + os.path.join(BASE_DIR, "instance", "ai_tutor.db")
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
