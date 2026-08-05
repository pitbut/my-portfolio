from app.models import Conversation, Message, Notification, User

from tests.conftest import register


def _login(client, email, password="password123"):
    client.post("/auth/login", data={"email": email, "password": password}, follow_redirects=True)


def test_chat_requires_auth(client):
    resp = client.get("/messages", follow_redirects=False)
    assert resp.status_code == 302
    assert "auth_required=1" in resp.headers["Location"]


def test_cannot_message_self(client):
    register(client, email="solo@example.com", role="customer")
    with client.application.app_context():
        user_id = User.query.filter_by(email="solo@example.com").first().id

    resp = client.get(f"/messages/u/{user_id}", follow_redirects=True)
    assert "Нельзя написать самому себе".encode() in resp.data


def test_two_executors_can_cooperate(client):
    """Кооперация производителей: сообщения не привязаны к заказу и не
    зависят от роли — оба участника могут быть исполнителями."""
    register(client, email="factory1@example.com", role="executor")
    with client.application.app_context():
        factory1_id = User.query.filter_by(email="factory1@example.com").first().id
    client.get("/auth/logout")

    register(client, email="factory2@example.com", role="executor")
    with client.application.app_context():
        factory2_id = User.query.filter_by(email="factory2@example.com").first().id

    resp = client.post(
        f"/messages/u/{factory1_id}", data={"body": "Есть свободные мощности для кооперации?"},
        follow_redirects=True,
    )
    assert "Есть свободные мощности для кооперации?".encode() in resp.data

    with client.application.app_context():
        conversation = Conversation.query.first()
        assert conversation is not None
        assert {conversation.user_a_id, conversation.user_b_id} == {factory1_id, factory2_id}
        assert Message.query.count() == 1

        notif = Notification.query.filter_by(user_id=factory1_id, type="direct_message").first()
        assert notif is not None

    client.get("/auth/logout")
    _login(client, "factory1@example.com")
    resp = client.get(f"/messages/u/{factory2_id}")
    assert "Есть свободные мощности для кооперации?".encode() in resp.data

    with client.application.app_context():
        message = Message.query.first()
        assert message.read_at is not None


def test_inbox_lists_conversation_with_unread_count(client):
    register(client, email="buyer@example.com", role="customer")
    with client.application.app_context():
        buyer_id = User.query.filter_by(email="buyer@example.com").first().id
    client.get("/auth/logout")

    register(client, email="constructor@example.com", role="executor")
    client.post(f"/messages/u/{buyer_id}", data={"body": "Готов взяться за проект"}, follow_redirects=True)
    client.get("/auth/logout")

    _login(client, "buyer@example.com")
    resp = client.get("/messages")
    assert "constructor@example.com".encode() in resp.data
    assert "Готов взяться за проект".encode() in resp.data
