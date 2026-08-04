"""Фабрика приложения B2B-платформы изготовителей и ремонтников оборудования."""
import os

from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
from flask import Flask
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

from config import config

load_dotenv()

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()
oauth = OAuth()
google_oauth = None  # регистрируется в create_app, если заданы GOOGLE_CLIENT_ID/SECRET


def create_app(config_name=None):
    global google_oauth

    config_name = config_name or os.environ.get("FLASK_CONFIG", "default")

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config[config_name])

    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Войдите, чтобы продолжить."
    login_manager.login_message_category = "info"

    oauth.init_app(app)
    if app.config.get("GOOGLE_CLIENT_ID") and app.config.get("GOOGLE_CLIENT_SECRET"):
        google_oauth = oauth.register(
            name="google",
            client_id=app.config["GOOGLE_CLIENT_ID"],
            client_secret=app.config["GOOGLE_CLIENT_SECRET"],
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email profile"},
        )
    else:
        google_oauth = None

    from app.i18n import register_i18n

    register_i18n(app)

    from app.routes.main import bp as main_bp
    from app.routes.auth import bp as auth_bp
    from app.routes.profile import bp as profile_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(profile_bp, url_prefix="/profile")

    from app import models  # noqa: F401 — регистрирует модели в metadata для миграций

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(models.User, int(user_id))

    @app.context_processor
    def inject_pending_confirmation():
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
    def inject_google_available():
        return {"google_login_available": google_oauth is not None}

    return app


def get_google_client():
    """google_oauth переприсваивается внутри create_app() при каждом запуске
    приложения (в т.ч. в тестах, где create_app вызывается многократно) —
    модули, импортировавшие имя один раз при старте, получили бы устаревшее
    значение. Поэтому обращаться к нему нужно только через эту функцию,
    читающую текущее значение глобальной переменной в момент вызова."""
    return google_oauth
