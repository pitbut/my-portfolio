from itsdangerous import URLSafeTimedSerializer

from app import db
from app.models import Message, User
from app.routes.auth import CONFIRM_SALT


def _login_admin(client, app):
    return client.post("/admin/login", data={"password": app.config["ADMIN_PASSWORD"]}, follow_redirects=True)


def _register_and_confirm(client, app, email):
    client.post(
        "/auth/register",
        data={"email": email, "password": "password123", "password2": "password123"},
    )
    with app.app_context():
        token = URLSafeTimedSerializer(app.config["SECRET_KEY"]).dumps(email, salt=CONFIRM_SALT)
    client.get(f"/auth/confirm/{token}")


def test_messages_requires_login(client):
    resp = client.get("/messages/")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


def test_user_can_message_admin(client, app):
    _register_and_confirm(client, app, "chatuser1@user.example")

    resp = client.post(
        "/messages/admin/send",
        data={"body": "Здравствуйте, вопрос по сайту."},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "Здравствуйте, вопрос по сайту.".encode() in resp.data

    with app.app_context():
        msg = Message.query.filter_by(body="Здравствуйте, вопрос по сайту.").first()
        assert msg is not None
        assert msg.recipient_user_id is None
        assert msg.sender_user_id is not None


def test_admin_can_reply_and_user_sees_it(client, app):
    _register_and_confirm(client, app, "chatuser2@user.example")
    client.post("/messages/admin/send", data={"body": "Вопрос от пользователя."})

    with app.app_context():
        user_id = User.query.filter_by(email="chatuser2@user.example").first().id

    client.get("/auth/logout")
    _login_admin(client, app)

    resp = client.get(f"/admin/users/{user_id}")
    assert "Вопрос от пользователя.".encode() in resp.data

    resp = client.post(
        f"/admin/users/{user_id}/message",
        data={"body": "Ответ администрации."},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "Ответ администрации.".encode() in resp.data

    with app.app_context():
        msg = Message.query.filter_by(body="Ответ администрации.").first()
        assert msg.sender_user_id is None
        assert msg.recipient_user_id == user_id


def test_unread_badge_appears_for_recipient(client, app):
    _register_and_confirm(client, app, "chatuser3@user.example")
    client.get("/auth/logout")

    _login_admin(client, app)
    with app.app_context():
        user_id = User.query.filter_by(email="chatuser3@user.example").first().id
    client.post(f"/admin/users/{user_id}/message", data={"body": "Проверка непрочитанного."})
    client.get("/admin/logout")

    client.post(
        "/auth/login",
        data={"email": "chatuser3@user.example", "password": "password123"},
    )
    resp = client.get("/")
    assert "unread-badge".encode() in resp.data

    resp = client.get("/messages/admin")
    assert "Проверка непрочитанного.".encode() in resp.data

    with app.app_context():
        msg = Message.query.filter_by(body="Проверка непрочитанного.").first()
        assert msg.is_read is True


def test_user_to_user_chat(client, app):
    _register_and_confirm(client, app, "chatusera@user.example")
    client.get("/auth/logout")
    _register_and_confirm(client, app, "chatuserb@user.example")

    with app.app_context():
        user_a_id = User.query.filter_by(email="chatusera@user.example").first().id

    resp = client.get("/messages/directory")
    # chatuserb (текущий пользователь) в своей же справочной странице не должен
    # предлагаться сам себе как собеседник — email в шапке сайта (текущая сессия)
    # не в счёт, важно, что его нет именно в списке карточек-пользователей.
    directory_list = resp.data.split(b'<div class="admin-list">', 1)[1]
    assert b"chatuserb@user.example" not in directory_list
    assert "chatusera@user.example".encode() in directory_list

    resp = client.post(
        f"/messages/user/{user_a_id}/send",
        data={"body": "Привет от B к A!"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "Привет от B к A!".encode() in resp.data

    client.get("/auth/logout")
    client.post(
        "/auth/login",
        data={"email": "chatusera@user.example", "password": "password123"},
    )
    resp = client.get("/messages/")
    assert "chatuserb@user.example".encode() in resp.data


def test_cannot_message_self(client, app):
    _register_and_confirm(client, app, "chatuserself@user.example")
    with app.app_context():
        user_id = User.query.filter_by(email="chatuserself@user.example").first().id
    resp = client.get(f"/messages/user/{user_id}")
    assert resp.status_code == 404


def test_delete_user_removes_their_messages(client, app):
    _register_and_confirm(client, app, "chatuserdel@user.example")
    client.post("/messages/admin/send", data={"body": "Сообщение перед удалением."})

    with app.app_context():
        user_id = User.query.filter_by(email="chatuserdel@user.example").first().id

    client.get("/auth/logout")
    _login_admin(client, app)
    client.post(f"/admin/users/{user_id}/delete")

    with app.app_context():
        assert Message.query.filter_by(body="Сообщение перед удалением.").first() is None
