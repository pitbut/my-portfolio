from app import db
from app.models import User


def test_register_creates_user_and_redirects_to_confirm_pending(client):
    response = client.post(
        "/auth/register",
        data={
            "name": "Аня",
            "email": "anya@example.com",
            "password": "password123",
            "password2": "password123",
        },
    )
    assert response.status_code == 302
    assert "/auth/confirm-pending" in response.headers["Location"]
    user = User.query.filter_by(email="anya@example.com").first()
    assert user is not None
    assert user.email_confirmed is False


def test_register_rejects_mismatched_passwords(client):
    response = client.post(
        "/auth/register",
        data={
            "name": "Аня",
            "email": "anya@example.com",
            "password": "password123",
            "password2": "different",
        },
    )
    assert response.status_code == 200
    assert User.query.filter_by(email="anya@example.com").first() is None


def test_login_with_wrong_password_fails(client, user):
    response = client.post(
        "/auth/login", data={"email": "student@example.com", "password": "wrong-password"}
    )
    assert response.status_code == 200
    assert b"\xd0\x9d\xd0\xb5\xd0\xb2\xd0\xb5\xd1\x80\xd0\xbd\xd1\x8b\xd0\xb9" in response.data  # "Неверный"


def test_login_success_redirects_to_dashboard(client, user):
    response = client.post(
        "/auth/login",
        data={"email": "student@example.com", "password": "password123"},
    )
    assert response.status_code == 302
    assert "/dashboard" in response.headers["Location"]


def test_unconfirmed_user_is_gated_to_confirm_pending_page(app, client):
    client.post(
        "/auth/register",
        data={
            "name": "Боря",
            "email": "borya@example.com",
            "password": "password123",
            "password2": "password123",
        },
    )

    response = client.get("/dashboard")
    assert response.status_code == 302
    assert "/auth/confirm-pending" in response.headers["Location"]

    response = client.get("/onboarding/avatar")
    assert response.status_code == 302
    assert "/auth/confirm-pending" in response.headers["Location"]


def test_confirm_pending_page_renders(client):
    client.post(
        "/auth/register",
        data={
            "name": "Гриша",
            "email": "grisha@example.com",
            "password": "password123",
            "password2": "password123",
        },
    )
    response = client.get("/auth/confirm-pending")
    assert response.status_code == 200
    assert "grisha@example.com".encode() in response.data


def test_confirmed_user_is_not_gated(app, client, user):
    client.post(
        "/auth/login",
        data={"email": "student@example.com", "password": "password123"},
    )

    response = client.get("/dashboard")
    assert response.status_code == 200


def test_confirm_link_unlocks_access(app, client):
    client.post(
        "/auth/register",
        data={
            "name": "Вера",
            "email": "vera@example.com",
            "password": "password123",
            "password2": "password123",
        },
    )
    with app.test_request_context():
        from app.routes.auth import confirm_url_for

        u = User.query.filter_by(email="vera@example.com").first()
        confirm_path = confirm_url_for(u).split("://", 1)[1].split("/", 1)[1]

    response = client.get(f"/{confirm_path}")
    assert response.status_code == 302

    with app.app_context():
        assert db.session.get(User, u.id).email_confirmed is True

    response = client.get("/dashboard")
    assert response.status_code != 302 or "/auth/confirm-pending" not in response.headers["Location"]
