from app import db
from app.models import TelegramLink, User

from tests.conftest import register


def _login_via_session(client, user_id):
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user_id)
        sess["_fresh"] = True


def test_homepage_shows_registration_stats_and_constructor_cta(client):
    register(client, email="cust@example.com", role="customer")
    client.get("/auth/logout")
    register(client, email="exec@example.com", role="executor")
    client.get("/auth/logout")
    register(client, email="constr@example.com", role="constructor")
    client.get("/auth/logout")

    resp = client.get("/")
    assert resp.status_code == 200
    assert b">3<" in resp.data  # общий счётчик "зарегистрировано всего"
    assert "/profile/constructor".encode() in resp.data


def test_google_signup_user_without_telegram_sees_reminder(client):
    # Пишем через тот же db.session, что использует тестовый app-контекст
    # фикстуры (client-запросы переиспользуют этот же контекст) — иначе
    # SQLAlchemy identity map в запросах не увидит изменения, сделанные
    # через отдельный вручную поднятый app_context.
    user = User(
        email="viagoogle@example.com", google_sub="fake-google-sub-123",
        role="customer", email_confirmed=True,
    )
    db.session.add(user)
    db.session.commit()
    user_id = user.id

    _login_via_session(client, user_id)

    client.application.config["TELEGRAM_BOT_TOKEN"] = "test-token"
    client.application.config["TELEGRAM_BOT_USERNAME"] = "test_bot"
    try:
        resp = client.get("/")
        assert "привяжите Telegram".encode() in resp.data

        db.session.add(TelegramLink(user_id=user_id, telegram_chat_id=123, notifications_enabled=True))
        db.session.commit()

        resp = client.get("/")
        assert "привяжите Telegram".encode() not in resp.data
    finally:
        client.application.config["TELEGRAM_BOT_TOKEN"] = None
        client.application.config["TELEGRAM_BOT_USERNAME"] = None


def test_no_reminder_for_password_signup_user(client):
    register(client, email="viapassword@example.com", role="customer")
    client.application.config["TELEGRAM_BOT_TOKEN"] = "test-token"
    client.application.config["TELEGRAM_BOT_USERNAME"] = "test_bot"
    try:
        resp = client.get("/")
        assert "привяжите Telegram".encode() not in resp.data
    finally:
        client.application.config["TELEGRAM_BOT_TOKEN"] = None
        client.application.config["TELEGRAM_BOT_USERNAME"] = None
