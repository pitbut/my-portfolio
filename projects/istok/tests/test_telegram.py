from itsdangerous import URLSafeTimedSerializer

from app import db, telegram_bot
from app.models import ContactMessage, Message, TelegramLink, TelegramLinkCode, User
from app.routes.auth import CONFIRM_SALT


def _register_and_confirm(client, app, email):
    client.post(
        "/auth/register",
        data={"email": email, "password": "password123", "password2": "password123"},
    )
    with app.app_context():
        token = URLSafeTimedSerializer(app.config["SECRET_KEY"]).dumps(email, salt=CONFIRM_SALT)
    client.get(f"/auth/confirm/{token}")


def test_telegram_settings_requires_login(client):
    resp = client.get("/messages/telegram")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


def test_telegram_settings_shows_deep_link_when_bot_configured(client, app):
    app.config["TELEGRAM_BOT_USERNAME"] = "IstokTestBot"
    _register_and_confirm(client, app, "tguser1@user.example")

    resp = client.get("/messages/telegram")
    assert resp.status_code == 200
    assert b"t.me/IstokTestBot" in resp.data


def test_webhook_rejects_wrong_secret(client, app):
    app.config["TELEGRAM_WEBHOOK_SECRET"] = "correct-secret"
    resp = client.post("/telegram/webhook/wrong-secret", json={})
    assert resp.status_code == 404


def test_webhook_links_account_via_start_token(client, app):
    app.config["TELEGRAM_WEBHOOK_SECRET"] = "s3cr3t"
    _register_and_confirm(client, app, "tguser2@user.example")

    with app.app_context():
        user = User.query.filter_by(email="tguser2@user.example").first()
        token = telegram_bot.link_token_for(user)

    resp = client.post(
        "/telegram/webhook/s3cr3t",
        json={"message": {"chat": {"id": 555, "username": "tguser2tg"}, "text": f"/start {token}"}},
    )
    assert resp.status_code == 200

    with app.app_context():
        link = TelegramLink.query.filter_by(telegram_chat_id=555).first()
        assert link is not None
        assert link.user.email == "tguser2@user.example"
        assert link.telegram_username == "tguser2tg"


def test_webhook_links_account_via_fallback_code(client, app):
    app.config["TELEGRAM_WEBHOOK_SECRET"] = "s3cr3t"
    _register_and_confirm(client, app, "tguser3@user.example")

    with app.app_context():
        user = User.query.filter_by(email="tguser3@user.example").first()
        code = telegram_bot.link_code_for(user)

    resp = client.post(
        "/telegram/webhook/s3cr3t",
        json={"message": {"chat": {"id": 777, "username": "tguser3tg"}, "text": code}},
    )
    assert resp.status_code == 200

    with app.app_context():
        assert TelegramLink.query.filter_by(telegram_chat_id=777).first() is not None
        # Код одноразовый — использованный удаляется.
        assert TelegramLinkCode.query.filter_by(code=code).first() is None


def test_unlink_removes_telegram_link(client, app):
    _register_and_confirm(client, app, "tguser4@user.example")

    with app.app_context():
        user = User.query.filter_by(email="tguser4@user.example").first()
        db.session.add(TelegramLink(user_id=user.id, telegram_chat_id=999))
        db.session.commit()

    resp = client.post("/messages/telegram/unlink", follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        assert TelegramLink.query.filter_by(telegram_chat_id=999).first() is None


def test_sending_message_notifies_linked_recipient(client, app, monkeypatch):
    _register_and_confirm(client, app, "sender@user.example")

    with app.app_context():
        recipient = User(email="recipient@user.example", email_confirmed=True)
        db.session.add(recipient)
        db.session.commit()
        db.session.add(TelegramLink(user_id=recipient.id, telegram_chat_id=42))
        db.session.commit()
        recipient_id = recipient.id

    sent = []
    monkeypatch.setattr(
        telegram_bot, "send_message", lambda chat_id, text: sent.append((chat_id, text)) or True
    )

    client.post(
        f"/messages/user/{recipient_id}/send",
        data={"body": "Здравствуйте! Вопрос по точке продажи."},
        follow_redirects=True,
    )

    assert len(sent) == 1
    chat_id, text = sent[0]
    assert chat_id == 42
    assert "Вопрос по точке продажи" in text

    with app.app_context():
        assert Message.query.filter_by(body="Здравствуйте! Вопрос по точке продажи.").first() is not None


def test_contact_form_notifies_admin_chat(client, app, monkeypatch):
    app.config["ADMIN_TELEGRAM_CHAT_ID"] = "12345"

    sent = []
    monkeypatch.setattr(
        telegram_bot, "send_message", lambda chat_id, text: sent.append((chat_id, text)) or True
    )

    client.post(
        "/contact",
        data={"name": "Пётр", "email": "petr@user.example", "message": "Где купить воду оптом?"},
        follow_redirects=True,
    )

    assert len(sent) == 1
    chat_id, text = sent[0]
    assert chat_id == "12345"
    assert "Где купить воду оптом?" in text
    assert "Пётр" in text

    with app.app_context():
        assert ContactMessage.query.filter_by(message="Где купить воду оптом?").first() is not None
