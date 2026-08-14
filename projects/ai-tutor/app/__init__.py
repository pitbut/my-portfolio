"""Фабрика приложения модуля «ИИ-репетитор»."""
import os

from dotenv import load_dotenv
from flask import Flask, redirect, request, url_for
from flask_login import LoginManager, current_user
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
    from app.routes.main import bp as main_bp
    from app.routes.onboarding import bp as onboarding_bp
    from app.routes.lesson import bp as lesson_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(onboarding_bp, url_prefix="/onboarding")
    app.register_blueprint(lesson_bp, url_prefix="/lesson")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    from app import models  # noqa: F401 — регистрирует модели в metadata для миграций

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(models.User, int(user_id))

    # Разделы auth/admin/static — исключение, чтобы (пере)отправить письмо,
    # выйти или зайти в /admin можно было и с неподтверждённым email.
    # Остальной сайт (кабинет, онбординг, занятия) недоступен, пока
    # email_confirmed не станет True — это единственное, что реально
    # проверяет, что ученик владеет своим почтовым ящиком, поэтому
    # обходной ссылки на подтверждение прямо на странице сайта нет (см.
    # app/routes/auth.py:_flash_confirmation_result — ссылку показываем
    # только в DEBUG, для локальной разработки без реального email).
    @app.before_request
    def require_email_confirmation():
        if not current_user.is_authenticated or current_user.email_confirmed:
            return None
        if request.blueprint in ("auth", "admin") or request.endpoint == "static":
            return None
        return redirect(url_for("auth.confirm_pending"))

    return app
