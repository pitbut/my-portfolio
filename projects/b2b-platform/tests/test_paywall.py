from werkzeug.security import generate_password_hash

from app import db
from app.models import User

from tests.conftest import register


def test_anonymous_cannot_reach_customer_profile(client):
    resp = client.get("/profile/customer", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["Location"].startswith("/") or "auth_required=1" in resp.headers["Location"]
    assert "auth_required=1" in resp.headers["Location"]


def test_anonymous_cannot_reach_executor_profile(client):
    resp = client.get("/profile/executor", follow_redirects=False)
    assert resp.status_code == 302
    assert "auth_required=1" in resp.headers["Location"]


def test_home_page_is_public(client):
    resp = client.get("/")
    assert resp.status_code == 200


def test_wrong_role_gets_forbidden(client):
    register(client, email="cust@example.com", role="customer")
    resp = client.get("/profile/executor")
    assert resp.status_code == 403


def test_authenticated_customer_reaches_own_profile(client):
    register(client, email="cust2@example.com", role="customer")
    resp = client.get("/profile/customer")
    assert resp.status_code == 200


def test_admin_bypasses_role_checks(client):
    with client.application.app_context():
        admin = User(email="admin@example.com", password_hash=generate_password_hash("adminpass123"), role="admin", email_confirmed=True)
        db.session.add(admin)
        db.session.commit()

    client.post("/auth/login", data={"email": "admin@example.com", "password": "adminpass123"}, follow_redirects=True)

    assert client.get("/profile/customer").status_code == 200
    assert client.get("/profile/executor").status_code == 200

    # без собственного customer_profile /orders/new честно отправляет
    # заполнить профиль (как и обычного заказчика) — здесь важно, что это
    # редирект на заполнение профиля, а не 403 "не твоя роль"
    resp = client.get("/orders/new", follow_redirects=False)
    assert resp.status_code == 302
    assert "/profile/customer" in resp.headers["Location"]
