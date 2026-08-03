"""Фабрика приложения "Исток"."""
import os

from dotenv import load_dotenv
from flask import Flask
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from config import config

load_dotenv()

db = SQLAlchemy()
migrate = Migrate()


def create_app(config_name=None):
    """Создаёт и настраивает экземпляр Flask-приложения."""
    config_name = config_name or os.environ.get("FLASK_CONFIG", "default")

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config[config_name])

    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)

    from app.routes.main import bp as main_bp
    from app.routes.sacred import bp as sacred_bp
    from app.routes.catalog import bp as catalog_bp
    from app.routes.articles import bp as articles_bp
    from app.routes.library import bp as library_bp
    from app.routes.admin import bp as admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(sacred_bp, url_prefix="/sacred")
    app.register_blueprint(catalog_bp, url_prefix="/catalog")
    app.register_blueprint(articles_bp, url_prefix="/articles")
    app.register_blueprint(library_bp, url_prefix="/library")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    from app import models  # noqa: F401 — регистрирует модели в metadata для миграций

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
