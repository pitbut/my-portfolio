from app import db
from app.models import Conversation, Message, SupportMessage, User, get_settings
from tests.conftest import admin_login, login


def test_protected_route_redirects_to_login(client):
    response = client.get("/admin/users")
    assert response.status_code == 302
    assert "/admin/login" in response.headers["Location"]


def test_wrong_password_rejected(client):
    response = client.post("/admin/login", data={"password": "definitely-wrong"})
    assert response.status_code == 200
    response = client.get("/admin/users")
    assert response.status_code == 302


def test_correct_password_grants_access(app, client):
    response = admin_login(app, client)
    assert response.status_code == 302
    response = client.get("/admin/users")
    assert response.status_code == 200


def test_block_single_user_prevents_login(app, client, user):
    admin_login(app, client)
    response = client.post(f"/admin/users/{user}/block", data={"reason": "тест"})
    assert response.status_code == 302

    with app.app_context():
        u = db.session.get(User, user)
        assert u.is_blocked is True
        assert u.blocked_reason == "тест"

    login_response = login(client)
    assert login_response.request.path == "/auth/login"

    response = client.post(f"/admin/users/{user}/block")
    with app.app_context():
        assert db.session.get(User, user).is_blocked is False


def test_block_all_and_unblock_all(app, client, user):
    admin_login(app, client)

    with app.app_context():
        other = User(name="Второй", email="second@example.com", password_hash="x", email_confirmed=True)
        db.session.add(other)
        db.session.commit()
        other_id = other.id

    client.post("/admin/users/block-all")
    with app.app_context():
        assert db.session.get(User, user).is_blocked is True
        assert db.session.get(User, other_id).is_blocked is True

    client.post("/admin/users/unblock-all")
    with app.app_context():
        assert db.session.get(User, user).is_blocked is False
        assert db.session.get(User, other_id).is_blocked is False


def test_kill_switch_blocks_public_site_but_not_admin(app, client, user):
    admin_login(app, client)
    client.post("/admin/settings/kill-switch", data={"disabled_message": "Технические работы"})

    with app.app_context():
        assert get_settings().app_enabled is False

    response = client.get("/", follow_redirects=True)
    assert response.status_code == 503
    assert "Технические работы" in response.get_data(as_text=True)

    admin_response = client.get("/admin/users")
    assert admin_response.status_code == 200

    client.post("/admin/settings/kill-switch")
    with app.app_context():
        assert get_settings().app_enabled is True


def test_update_limits_toggle_and_default(app, client):
    admin_login(app, client)
    client.post("/admin/settings/limits", data={"default_message_limit": "5"})
    with app.app_context():
        settings = get_settings()
        assert settings.limits_enabled is False  # чекбокс не был передан — снят
        assert settings.default_message_limit == 5

    client.post("/admin/settings/limits", data={"limits_enabled": "on", "default_message_limit": "10"})
    with app.app_context():
        settings = get_settings()
        assert settings.limits_enabled is True
        assert settings.default_message_limit == 10


def test_set_and_clear_message_limit(app, client, user):
    admin_login(app, client)

    client.post(f"/admin/users/{user}/limit", data={"message_limit": "3"})
    with app.app_context():
        assert db.session.get(User, user).message_limit == 3

    client.post(f"/admin/users/{user}/limit", data={"message_limit": ""})
    with app.app_context():
        assert db.session.get(User, user).message_limit is None


def test_reset_usage(app, client, user):
    admin_login(app, client)
    with app.app_context():
        u = db.session.get(User, user)
        u.messages_used = 7
        db.session.commit()

    client.post(f"/admin/users/{user}/reset-usage")
    with app.app_context():
        assert db.session.get(User, user).messages_used == 0


def test_toggle_paid(app, client, user):
    admin_login(app, client)
    client.post(f"/admin/users/{user}/paid")
    with app.app_context():
        assert db.session.get(User, user).is_paid is True
    client.post(f"/admin/users/{user}/paid")
    with app.app_context():
        assert db.session.get(User, user).is_paid is False


def test_delete_user_cascades_conversations(app, client, user):
    admin_login(app, client)

    with app.app_context():
        conv = Conversation(user_id=user, companion_key="tamada")
        db.session.add(conv)
        db.session.flush()
        db.session.add(Message(conversation_id=conv.id, sender="user", content="Привет"))
        db.session.add(SupportMessage(user_id=user, sender="user", body="Помогите"))
        db.session.commit()
        conv_id = conv.id

    client.post(f"/admin/users/{user}/delete")

    with app.app_context():
        assert db.session.get(User, user) is None
        assert db.session.get(Conversation, conv_id) is None
        assert SupportMessage.query.filter_by(user_id=user).count() == 0


def test_admin_can_reply_to_support(app, client, user):
    admin_login(app, client)
    with app.app_context():
        db.session.add(SupportMessage(user_id=user, sender="user", body="Оплатил, но не работает"))
        db.session.commit()

    response = client.post(f"/admin/support/{user}", data={"body": "Разбираемся, спасибо!"})
    assert response.status_code == 302

    with app.app_context():
        reply = SupportMessage.query.filter_by(user_id=user, sender="admin").first()
        assert reply is not None
        assert reply.body == "Разбираемся, спасибо!"
