from werkzeug.security import check_password_hash

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


def test_login_sets_persistent_remember_cookie(client):
    """Мобильное приложение (Capacitor-обёртка) убивается системой Android
    в фоне намного агрессивнее браузера — обычная сессионная кука
    (без Max-Age) при этом теряется, и пользователю приходится логиниться
    заново при каждом запуске. login_user(..., remember=True) выдаёт
    долгоживущую remember-куку поверх сессионной, чтобы вход переживал
    перезапуск процесса."""
    register(client, email="remember@example.com", password="password123", role="executor")
    client.get("/auth/logout")

    client.post("/auth/login", data={"email": "remember@example.com", "password": "password123"})

    remember_cookie = client.get_cookie("remember_token")
    assert remember_cookie is not None
    assert remember_cookie.expires is not None  # не сессионная — переживает закрытие приложения


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


def _reset_path_for(client, email):
    from app.routes.auth import reset_url_for

    with client.application.test_request_context():
        with client.application.app_context():
            user = User.query.filter_by(email=email).first()
            url = reset_url_for(user)
    return url.split("localhost", 1)[-1] if "localhost" in url else url


def test_forgot_password_shows_reset_link_when_resend_not_configured(client):
    register(client, email="reset@example.com", password="oldpassword1")
    client.get("/auth/logout")

    resp = client.post("/auth/forgot-password", data={"email": "reset@example.com"}, follow_redirects=True)
    assert "ссылка для сброса пароля".encode() in resp.data
    assert "/auth/reset-password/".encode() in resp.data


def test_forgot_password_same_message_for_unknown_email(client):
    resp = client.post("/auth/forgot-password", data={"email": "nobody@example.com"}, follow_redirects=True)
    assert "Если такой email зарегистрирован".encode() in resp.data


def test_reset_password_updates_hash_and_allows_login(client):
    register(client, email="reset2@example.com", password="oldpassword1")
    client.get("/auth/logout")

    path = _reset_path_for(client, "reset2@example.com")
    resp = client.post(path, data={"password": "newpassword1", "password2": "newpassword1"}, follow_redirects=True)
    assert "Пароль обновлён".encode() in resp.data

    with client.application.app_context():
        user = User.query.filter_by(email="reset2@example.com").first()
        assert check_password_hash(user.password_hash, "newpassword1")
        assert not check_password_hash(user.password_hash, "oldpassword1")

    resp = client.post("/auth/login", data={"email": "reset2@example.com", "password": "newpassword1"}, follow_redirects=False)
    assert resp.status_code == 302


def test_reset_password_rejects_mismatched_passwords(client):
    register(client, email="reset3@example.com", password="oldpassword1")
    client.get("/auth/logout")

    path = _reset_path_for(client, "reset3@example.com")
    resp = client.post(path, data={"password": "newpassword1", "password2": "different1"}, follow_redirects=True)
    assert "не совпадают".encode() in resp.data

    with client.application.app_context():
        user = User.query.filter_by(email="reset3@example.com").first()
        assert check_password_hash(user.password_hash, "oldpassword1")


def test_reset_password_rejects_invalid_token(client):
    resp = client.get("/auth/reset-password/not-a-real-token", follow_redirects=True)
    assert "недействительна".encode() in resp.data
