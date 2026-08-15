"""Создаёт первого администратора из ADMIN_EMAIL/ADMIN_PASSWORD, если он ещё
не существует. Запускается один раз при деплое, после `flask db upgrade`."""
import os

from werkzeug.security import generate_password_hash

from app import create_app, db
from app.models import User

app = create_app(os.environ.get("FLASK_CONFIG"))

with app.app_context():
    admin_email = app.config.get("ADMIN_EMAIL")
    admin_password = app.config.get("ADMIN_PASSWORD")

    if not admin_email or not admin_password:
        print("ADMIN_EMAIL/ADMIN_PASSWORD не заданы — пропускаю создание администратора.")
    else:
        existing = User.query.filter_by(email=admin_email.lower()).first()
        if existing:
            if not existing.is_admin:
                existing.is_admin = True
                db.session.commit()
                print(f"Пользователь {admin_email} назначен администратором.")
            else:
                print(f"Администратор {admin_email} уже существует.")
        else:
            admin = User(
                email=admin_email.lower(),
                password_hash=generate_password_hash(admin_password),
                email_confirmed=True,
                is_admin=True,
            )
            db.session.add(admin)
            db.session.commit()
            print(f"Создан администратор {admin_email}.")
