from app.models import User


def test_register_creates_user_and_redirects_to_onboarding(client):
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
    assert "/onboarding/avatar" in response.headers["Location"]
    assert User.query.filter_by(email="anya@example.com").first() is not None


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
