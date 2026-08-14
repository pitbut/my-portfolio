from app import db
from app.avatars import AVATAR_CHOICES
from app.models import User
from tests.conftest import login


def test_register_redirects_to_confirm_pending_not_avatar_step(client):
    """Онбординг (выбор аватара) начинается только после подтверждения
    email — см. before_request-гейт в app/__init__.py."""
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


def test_confirmed_user_reaches_avatar_step(app, client):
    with app.app_context():
        client.post(
            "/auth/register",
            data={
                "name": "Аня",
                "email": "anya@example.com",
                "password": "password123",
                "password2": "password123",
            },
        )
        u = User.query.filter_by(email="anya@example.com").first()
        u.email_confirmed = True
        db.session.commit()

        response = client.get("/onboarding/avatar")
        assert response.status_code == 200


def test_choose_avatar_sets_avatar_and_voice(app, client, user):
    with app.app_context():
        login(client)
        response = client.post(
            "/onboarding/avatar",
            data={"avatar_key": "nova", "voice_name": "Google russian"},
        )
        assert response.status_code == 302
        assert "/onboarding/subject" in response.headers["Location"]

        u = db.session.get(User, user)
        assert u.avatar_key == "nova"
        assert u.voice_name == "Google russian"
        assert u.avatar["name"] == "Нова"


def test_choose_avatar_rejects_unknown_key(app, client, user):
    with app.app_context():
        login(client)
        response = client.post("/onboarding/avatar", data={"avatar_key": "not-a-real-avatar"})
        assert response.status_code == 200

        u = db.session.get(User, user)
        assert u.avatar_key == "alex"  # не изменился


def test_user_without_avatar_key_falls_back_to_default():
    default = AVATAR_CHOICES[0]
    u = User(name="Тест", email="t@example.com", password_hash="x")
    assert u.avatar == default
