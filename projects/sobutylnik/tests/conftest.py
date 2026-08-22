import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from werkzeug.security import generate_password_hash

from app import create_app, db
from app.models import User


@pytest.fixture()
def app():
    app = create_app("testing")

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def user(app):
    """Создаёт подтверждённого пользователя с выбранным собеседником.

    Возвращается id, а не сам ORM-объект — используйте db.session.get(User, user)
    внутри собственного app.app_context()."""
    with app.app_context():
        u = User(
            name="Тестовый пользователь",
            email="user@example.com",
            password_hash=generate_password_hash("password123"),
            email_confirmed=True,
            companion_key="tamada",
        )
        db.session.add(u)
        db.session.commit()
        return u.id


def login(client, email="user@example.com", password="password123"):
    return client.post("/auth/login", data={"email": email, "password": password}, follow_redirects=True)


def admin_login(app, client):
    with app.app_context():
        password = app.config["ADMIN_PASSWORD"]
    return client.post("/admin/login", data={"password": password})
