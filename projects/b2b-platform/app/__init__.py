"""Фабрика приложения B2B-платформы изготовителей и ремонтников оборудования."""
import os

from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
from flask import Flask, render_template
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import event
from sqlalchemy.engine import Engine

from app.cli import register_cli
from config import config

load_dotenv()


@event.listens_for(Engine, "connect")
def _enforce_sqlite_foreign_keys(dbapi_connection, connection_record):
    """PostgreSQL (продакшн) всегда проверяет внешние ключи, а SQLite
    (тесты и локальная разработка) — нет, если явно не включить. Без этого
    тесты не замечали бы нарушения FK, которые в проде дадут IntegrityError."""
    if type(dbapi_connection).__module__.startswith("sqlite3"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


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
    from app.routes.orders import bp as orders_bp
    from app.routes.map import bp as map_bp
    from app.routes.reviews import bp as reviews_bp
    from app.routes.disputes import bp as disputes_bp
    from app.routes.admin import bp as admin_bp
    from app.routes.marketplace import bp as marketplace_bp
    from app.routes.jobs import bp as jobs_bp
    from app.routes.materials_market import bp as materials_market_bp
    from app.routes.chat import bp as chat_bp
    from app.routes.constructors import bp as constructors_bp
    from app.routes.settings import bp as settings_bp
    from app.routes.telegram import bp as telegram_bp
    from app.routes.push import bp as push_bp
    from app.routes.search import bp as search_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(profile_bp, url_prefix="/profile")
    app.register_blueprint(orders_bp)
    app.register_blueprint(map_bp)
    app.register_blueprint(reviews_bp)
    app.register_blueprint(disputes_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(marketplace_bp)
    app.register_blueprint(jobs_bp)
    app.register_blueprint(materials_market_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(constructors_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(telegram_bp)
    csrf.exempt(telegram_bp)  # вебхук Telegram не может передать наш CSRF-токен
    app.register_blueprint(push_bp)
    app.register_blueprint(search_bp)

    register_cli(app)

    from app import models  # noqa: F401 — регистрирует модели в metadata для миграций

    app.jinja_env.globals["payment_method_choices"] = models.PAYMENT_METHOD_CHOICES
    app.jinja_env.globals["delivery_choices"] = models.DELIVERY_CHOICES
    app.jinja_env.globals["csv_to_codes"] = models.csv_to_codes
    app.jinja_env.globals["payment_method_labels"] = lambda value: models.csv_to_labels(value, models.PAYMENT_METHOD_LABELS)
    app.jinja_env.globals["delivery_label"] = lambda value: models.DELIVERY_LABELS.get(value)
    app.jinja_env.globals["workload_color"] = models.workload_color

    from app.telegram_bot import deep_link_for_current_user, link_code_for_current_user

    app.jinja_env.globals["telegram_deep_link"] = deep_link_for_current_user
    app.jinja_env.globals["telegram_link_code"] = link_code_for_current_user

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

    @app.context_processor
    def inject_telegram_bot_available():
        return {
            "telegram_bot_available": bool(
                app.config.get("TELEGRAM_BOT_TOKEN") and app.config.get("TELEGRAM_BOT_USERNAME")
            )
        }

    @app.errorhandler(403)
    def forbidden(error):
        return render_template(
            "errors/error.html", code=403, heading="Доступ запрещён",
            message="У вас нет прав на просмотр этой страницы — возможно, она относится к другой роли или другому пользователю.",
        ), 403

    @app.errorhandler(404)
    def not_found(error):
        return render_template(
            "errors/error.html", code=404, heading="Страница не найдена",
            message="Такой страницы не существует, либо она была удалена.",
        ), 404

    @app.errorhandler(500)
    def server_error(error):
        return render_template(
            "errors/error.html", code=500, heading="Ошибка сервера",
            message="Что-то пошло не так на нашей стороне. Мы уже знаем об этом — попробуйте обновить страницу чуть позже.",
        ), 500

    @app.context_processor
    def inject_unread_notifications():
        from flask_login import current_user

        if current_user.is_authenticated:
            from app.notify import unread_count

            return {"unread_notifications": unread_count(current_user)}
        return {"unread_notifications": 0}

    @app.context_processor
    def inject_unread_messages():
        from flask_login import current_user

        if current_user.is_authenticated:
            from app.models import Conversation, Message

            count = (
                Message.query.join(Conversation, Message.conversation_id == Conversation.id)
                .filter(
                    db.or_(Conversation.user_a_id == current_user.id, Conversation.user_b_id == current_user.id),
                    Message.sender_id != current_user.id,
                    Message.read_at.is_(None),
                )
                .count()
            )
            return {"unread_messages": count}
        return {"unread_messages": 0}

    return app


def get_google_client():
    """google_oauth переприсваивается внутри create_app() при каждом запуске
    приложения (в т.ч. в тестах, где create_app вызывается многократно) —
    модули, импортировавшие имя один раз при старте, получили бы устаревшее
    значение. Поэтому обращаться к нему нужно только через эту функцию,
    читающую текущее значение глобальной переменной в момент вызова."""
    return google_oauth
