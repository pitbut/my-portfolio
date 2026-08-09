from app.models import Conversation, Message, Notification, Order, User

from tests.conftest import register
from tests.test_orders import _create_order, _setup_customer, _setup_executor


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


def test_new_messages_polling_returns_and_marks_read(client):
    """Страница диалога опрашивает этот эндпоинт раз в несколько секунд
    (см. thread.html), чтобы сообщения появлялись без ручного обновления."""
    register(client, email="poll1@example.com", role="executor")
    with client.application.app_context():
        user1_id = User.query.filter_by(email="poll1@example.com").first().id
    client.get("/auth/logout")

    register(client, email="poll2@example.com", role="executor")
    with client.application.app_context():
        user2_id = User.query.filter_by(email="poll2@example.com").first().id

    client.post(f"/messages/u/{user1_id}", data={"body": "Привет"})

    resp = client.get(f"/messages/u/{user1_id}/new.json?after_id=0")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["messages"]) == 1
    assert data["messages"][0]["body"] == "Привет"
    assert data["messages"][0]["own"] is True

    client.get("/auth/logout")
    _login(client, "poll1@example.com")
    resp2 = client.get(f"/messages/u/{user2_id}/new.json?after_id=0")
    data2 = resp2.get_json()
    assert data2["messages"][0]["own"] is False

    with client.application.app_context():
        message = Message.query.first()
        assert message.read_at is not None  # опрос второй стороны пометил прочитанным

    resp3 = client.get(f"/messages/u/{user2_id}/new.json?after_id={data2['messages'][0]['id']}")
    assert resp3.get_json()["messages"] == []


def test_chat_shows_order_context_banner_when_both_sides_involved(client):
    """?order_id= в ссылке на чат должен показывать баннер с номером заявки —
    но только если оба собеседника реально стороны именно по этой заявке
    (иначе номер можно было бы подставить произвольно и ввести в заблуждение)."""
    region_id = _setup_customer(client, "cust@example.com")
    service_id, _ = _setup_executor(client, "exec@example.com", region_id)

    with client.application.app_context():
        customer_user_id = User.query.filter_by(email="cust@example.com").first().id
        executor_user_id = User.query.filter_by(email="exec@example.com").first().id

    _login(client, "cust@example.com")
    _create_order(client, region_id, service_id)
    with client.application.app_context():
        order_id = Order.query.first().id
    client.get("/auth/logout")

    _login(client, "exec@example.com")
    client.post(
        f"/orders/{order_id}/bid",
        data={"price": "500000", "currency": "UZS", "lead_time_days": "5"},
        follow_redirects=True,
    )

    resp = client.get(f"/messages/u/{customer_user_id}?order_id={order_id}")
    assert f"Обсуждаете заявку".encode() in resp.data
    assert f"№{order_id}".encode() in resp.data
    client.get("/auth/logout")

    # заявка не при чём к этой паре — левый order_id должен молча игнорироваться
    register(client, email="stranger@example.com", role="executor")
    resp = client.get(f"/messages/u/{customer_user_id}?order_id={order_id}")
    assert "Обсуждаете заявку".encode() not in resp.data


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
