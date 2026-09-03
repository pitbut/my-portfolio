from flask import Flask, send_from_directory

import config


def create_app() -> Flask:
    app = Flask(__name__, static_folder=str(config.BASE_DIR / "static"))

    from .public_routes import public_bp
    from .admin_routes import admin_bp

    app.register_blueprint(public_bp, url_prefix="/api")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")

    static_dir = config.BASE_DIR / "static"

    @app.route("/")
    def demo_page():
        return send_from_directory(static_dir, "index.html")

    @app.route("/admin")
    def admin_page():
        return send_from_directory(static_dir / "admin", "index.html")

    return app
