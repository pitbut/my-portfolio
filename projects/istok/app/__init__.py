"""Фабрика приложения "Исток"."""
import os

from dotenv import load_dotenv
from flask import Flask
from flask_login import LoginManager
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

    from app.routes.main import bp as main_bp
    from app.routes.sacred import bp as sacred_bp
    from app.routes.catalog import bp as catalog_bp
    from app.routes.articles import bp as articles_bp
    from app.routes.library import bp as library_bp
    from app.routes.admin import bp as admin_bp
    from app.routes.auth import bp as auth_bp
    from app.routes.reviews import bp as reviews_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(sacred_bp, url_prefix="/sacred")
    app.register_blueprint(catalog_bp, url_prefix="/catalog")
    app.register_blueprint(articles_bp, url_prefix="/articles")
    app.register_blueprint(library_bp, url_prefix="/library")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(reviews_bp, url_prefix="/reviews")

    from app import models  # noqa: F401 — регистрирует модели в metadata для миграций

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(models.User, int(user_id))

    @app.context_processor
    def inject_pending_confirmation():
        """Пока на сервере не настроена реальная отправка почты (RESEND_API_KEY),
        показываем ссылку подтверждения прямо на сайте, а не только один раз
        во flash-сообщении, — иначе её легко потерять."""
        from flask_login import current_user

        if (
            current_user.is_authenticated
            and not current_user.email_confirmed
            and not app.config.get("RESEND_API_KEY")
        ):
            from app.routes.auth import confirm_url_for

            return {"pending_confirm_url": confirm_url_for(current_user)}
        return {}

    @app.template_global()
    def image_url(value):
        """Разрешает значение поля image_url/cover_url в готовую ссылку.

        Если это внешняя ссылка (http/https) — используется как есть.
        Иначе считается путём внутри app/static/img/ (например,
        "sacred/lourdes.jpg" -> /static/img/sacred/lourdes.jpg) — так
        картинки можно просто класть файлом в репозиторий."""
        if not value:
            return None
        if value.startswith("http://") or value.startswith("https://"):
            return value
        from flask import url_for

        return url_for("static", filename=f"img/{value}")

    return app
