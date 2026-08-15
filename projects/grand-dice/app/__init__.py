"""Фабрика приложения Grand Dice Casino."""
import os

from dotenv import load_dotenv

# Должно выполниться до "from config import config" — config.py читает
# переменные окружения (в т.ч. DATABASE_URL) на уровне определения классов,
# а `flask` CLI подгружает .env самостоятельно ДО импорта этого модуля.
# Если .env загрузить здесь позже, файл-конфигурация уже успеет прочитать
# пустые/отсутствующие значения и не встанет на дефолты (например, SQLite).
load_dotenv()

from flask import Flask, request, session
from flask_babel import Babel
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from config import config

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
babel = Babel()


def _select_locale():
    """Язык интерфейса: явный выбор игрока (сессия) > язык браузера > русский."""
    from flask import current_app

    languages = current_app.config["LANGUAGES"]
    if session.get("lang") in languages:
        return session["lang"]
    return request.accept_languages.best_match(languages.keys()) or current_app.config["BABEL_DEFAULT_LOCALE"]


def create_app(config_name=None):
    """Создаёт и настраивает экземпляр Flask-приложения."""
    config_name = config_name or os.environ.get("FLASK_CONFIG", "default")

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config[config_name])

    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Войдите, чтобы продолжить."
    login_manager.login_message_category = "info"
    babel.init_app(app, locale_selector=_select_locale)

    from app.routes.main import bp as main_bp
    from app.routes.auth import bp as auth_bp
    from app.routes.game import bp as game_bp
    from app.routes.wallet import bp as wallet_bp
    from app.routes.support import bp as support_bp
    from app.routes.admin import bp as admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(game_bp, url_prefix="/game")
    app.register_blueprint(wallet_bp, url_prefix="/wallet")
    app.register_blueprint(support_bp, url_prefix="/support")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    from app import models  # noqa: F401 — регистрирует модели в metadata для миграций

    @login_manager.user_loader
    def load_user(user_id):
        user = db.session.get(models.User, int(user_id))
        # Если админ заблокировал игрока прямо во время его сессии — тот
        # сразу теряет доступ (Flask-Login считает сессию недействительной),
        # а не только при следующей попытке входа.
        if user is not None and user.is_currently_blocked():
            return None
        return user

    @app.context_processor
    def inject_pending_confirmation():
        """Пока на сервере не настроена реальная отправка почты
        (RESEND_API_KEY), показываем ссылку подтверждения прямо на сайте,
        а не только один раз во flash-сообщении, — иначе её легко потерять."""
        from flask_login import current_user

        if (
            current_user.is_authenticated
            and not current_user.email_confirmed
            and not app.config.get("RESEND_API_KEY")
        ):
            from app.routes.auth import confirm_url_for

            return {"pending_confirm_url": confirm_url_for(current_user)}
        return {}

    @app.context_processor
    def inject_i18n_and_currency():
        """Курсы валют и список языков — нужны в base.html на каждой
        странице (переключатели в шапке), поэтому проще внедрить их
        контекст-процессором, чем передавать из каждого view."""
        from app.currency import SUPPORTED_CURRENCIES, get_cached_rates

        return {
            "fx_rates": get_cached_rates(),
            "fx_currencies": SUPPORTED_CURRENCIES,
            "languages": app.config["LANGUAGES"],
            "current_lang": _select_locale(),
        }

    return app
