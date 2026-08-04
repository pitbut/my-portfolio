from app.models import User

from tests.conftest import register


def test_register_creates_user_and_logs_in(client):
    resp = register(client, email="new@example.com", role="customer")
    assert resp.status_code == 200
    with client.application.app_context():
        user = User.query.filter_by(email="new@example.com").first()
        assert user is not None
        assert user.role == "customer"
        assert user.password_hash is not None


def test_register_rejects_short_password(client):
    resp = client.post(
        "/auth/register",
        data={"email": "x@example.com", "password": "short", "password2": "short", "role": "customer", "language": "ru"},
        follow_redirects=True,
    )
    assert "не короче 8 символов".encode() in resp.data or "8 символов".encode() in resp.data


def test_register_rejects_duplicate_email(client):
    register(client, email="dup@example.com")
    client.get("/auth/logout")
    resp = register(client, email="dup@example.com")
    assert "уже зарегистрирован".encode() in resp.data


def test_login_wrong_password(client):
    register(client, email="login@example.com", password="password123")
    client.get("/auth/logout")
    resp = client.post(
        "/auth/login", data={"email": "login@example.com", "password": "wrong-pass"}, follow_redirects=True,
    )
    assert "Неверный email или пароль".encode() in resp.data


def test_login_success_redirects_to_profile(client):
    register(client, email="login2@example.com", password="password123", role="executor")
    client.get("/auth/logout")
    resp = client.post(
        "/auth/login", data={"email": "login2@example.com", "password": "password123"}, follow_redirects=False,
    )
    assert resp.status_code == 302
    assert "/profile/executor" in resp.headers["Location"]


def test_email_confirmation_flow(client):
    register(client, email="confirm@example.com")
    with client.application.app_context():
        user = User.query.filter_by(email="confirm@example.com").first()
        assert user.email_confirmed is False

    from app.routes.auth import confirm_url_for

    with client.application.test_request_context():
        with client.application.app_context():
            user = User.query.filter_by(email="confirm@example.com").first()
            url = confirm_url_for(user)

    path = url.split("localhost", 1)[-1] if "localhost" in url else url
    resp = client.get(path, follow_redirects=True)
    assert resp.status_code == 200

    with client.application.app_context():
        user = User.query.filter_by(email="confirm@example.com").first()
        assert user.email_confirmed is True
