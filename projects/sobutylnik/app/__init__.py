"""Фабрика приложения «Собутыльник»."""
import os

from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, url_for
from flask_login import LoginManager, current_user, logout_user
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from config import config

load_dotenv()

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()


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

    from app.routes.admin import bp as admin_bp
    from app.routes.auth import bp as auth_bp
    from app.routes.chat import bp as chat_bp
    from app.routes.main import bp as main_bp
    from app.routes.support import bp as support_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(chat_bp, url_prefix="/room")
    app.register_blueprint(support_bp, url_prefix="/support")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    from app import models  # noqa: F401 — регистрирует модели в metadata для миграций

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(models.User, int(user_id))

    # Единый гейт доступа, в порядке проверки:
    #  1) общий рубильник администратора («полностью вся программа») —
    #     блокирует вообще всех, кроме самой админ-панели;
    #  2) индивидуальная блокировка пользователя («по одному») —
    #     разлогинивает и не пускает дальше публичных страниц;
    #  3) подтверждение email — тот же паттерн, что в ai-tutor: пока
    #     ученик/гость не подтвердил почту, сайт (кроме auth/admin/static)
    #     недоступен — это единственная реальная проверка владения
    #     почтовым ящиком.
    @app.before_request
    def access_gate():
        if request.blueprint == "admin" or request.endpoint == "static":
            return None

        settings = models.get_settings()
        if not settings.app_enabled:
            return render_template("main/disabled.html", message=settings.disabled_message), 503

        if current_user.is_authenticated and current_user.is_blocked:
            logout_user()
            flash("Ваш аккаунт заблокирован администратором. Обратитесь в поддержку.", "error")
            return redirect(url_for("main.index"))

        if current_user.is_authenticated and not current_user.email_confirmed:
            if request.blueprint == "auth":
                return None
            return redirect(url_for("auth.confirm_pending"))

        return None

    return app
