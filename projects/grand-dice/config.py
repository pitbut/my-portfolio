"""Конфигурация приложения. Значения читаются из переменных окружения (.env)."""
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _normalize_db_url(url):
    """Некоторые хостинги отдают DATABASE_URL со схемой postgres://,
    которую современный SQLAlchemy не принимает — нужен postgresql://."""
    if url and url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


class Config:
    """Базовая конфигурация, общая для всех окружений."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Жёсткий лимit на размер запроса (защита от заливки огромных файлов в
    # чат поддержки) — с запасом над MAX_PHOTO_BYTES из app/uploads.py.
    MAX_CONTENT_LENGTH = 6 * 1024 * 1024

    # Пароль администратора больше не используется напрямую — админ это
    # обычный пользователь с флагом is_admin=True (см. seed.py). Значение
    # ниже нужно только seed.py при первом создании такого аккаунта.
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")

    # Письма (подтверждение регистрации, OTP на вывод средств) отправляются
    # через HTTP-API Resend, а не через SMTP — большинство хостингов блокируют
    # исходящие SMTP-соединения на бесплатном тарифе. Если RESEND_API_KEY не
    # задан, письма не отправляются по-настоящему — текст пишется в лог и
    # (только в DEBUG) показывается прямо на странице, чтобы не блокировать
    # разработку без настроенной почты.
    RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER") or "Grand Dice <onboarding@resend.dev>"

    # Срок жизни ссылки подтверждения email, в секундах (по умолчанию сутки).
    CONFIRM_TOKEN_MAX_AGE = int(os.environ.get("CONFIRM_TOKEN_MAX_AGE", 86400))

    # Срок жизни ссылки восстановления пароля, в секундах (по умолчанию час —
    # короче, чем подтверждение email, т.к. эта ссылка даёт доступ к аккаунту).
    RESET_TOKEN_MAX_AGE = int(os.environ.get("RESET_TOKEN_MAX_AGE", 3600))

    # Срок жизни OTP-кода на вывод средств, в секундах.
    OTP_MAX_AGE = int(os.environ.get("OTP_MAX_AGE", 600))

    # Стартовый демо-баланс для новых аккаунтов (виртуальные средства для
    # тестового режима — реальных денег не затрагивает).
    STARTING_DEMO_BALANCE = int(os.environ.get("STARTING_DEMO_BALANCE", 1000))

    # Комиссия казино в игре в кости, в процентах (влияет на множитель выплаты).
    HOUSE_EDGE_PERCENT = float(os.environ.get("HOUSE_EDGE_PERCENT", 1.0))

    # Приём/выдача реальных денег пока идёт как заявки, обрабатываемые
    # вручную администратором — интеграция с Click API появится позже.
    # Ограничения ниже — просто разумные значения по умолчанию.
    MIN_WITHDRAW_AMOUNT = float(os.environ.get("MIN_WITHDRAW_AMOUNT", 10))
    MIN_DEPOSIT_AMOUNT = float(os.environ.get("MIN_DEPOSIT_AMOUNT", 10))

    # Ключ шифрования номеров карт (Fernet). Без него User.card_number /
    # WalletRequest.card_number не сохраняются — см. app/crypto.py.
    CARD_ENCRYPTION_KEY = os.environ.get("CARD_ENCRYPTION_KEY")


class DevelopmentConfig(Config):
    DEBUG = True
    # "or", не get(key, default): переменная может прийти пустой строкой, а
    # не отсутствующей (в т.ч. если `flask` CLI подгрузило .env с
    # DATABASE_URL= раньше нас) — get(..., default) в этом случае не
    # подставит дефолт, т.к. ключ формально присутствует.
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or (
        "sqlite:///" + os.path.join(BASE_DIR, "instance", "grand_dice.db")
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
