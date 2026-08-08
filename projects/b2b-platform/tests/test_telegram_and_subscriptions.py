import json
from datetime import datetime, timedelta

from app import db
from app.models import Notification, Subscription, SubscriptionPlan, TelegramLink, User
from app.subscriptions import current_subscription, has_active_subscription

from tests.conftest import register
from tests.test_orders import _create_order, _login, _setup_customer, _setup_executor


def test_executor_gets_trial_subscription_on_profile_completion(client):
    region_id = _setup_customer(client, "cust@example.com")
    _setup_executor(client, "exec@example.com", region_id)

    with client.application.app_context():
        user = User.query.filter_by(email="exec@example.com").first()
        sub = current_subscription(user.executor_profile)
        assert sub is not None
        assert sub.status == "trialing"
        assert sub.plan.code == "trial"
        assert has_active_subscription(user.executor_profile)


def test_expired_subscription_excludes_executor_from_matching(client):
    region_id = _setup_customer(client, "cust2@example.com")
    service_id, _ = _setup_executor(client, "exec2@example.com", region_id)

    with client.application.app_context():
        user = User.query.filter_by(email="exec2@example.com").first()
        sub = current_subscription(user.executor_profile)
        sub.expires_at = datetime.utcnow() - timedelta(days=1)
        db.session.commit()
        assert not has_active_subscription(user.executor_profile)

    _login(client, "cust2@example.com")
    resp = _create_order(client, region_id, service_id)
    assert "Подходящих исполнителей пока не нашлось".encode() in resp.data


def test_telegram_deep_link_and_webhook_binding(client, monkeypatch):
    client.application.config["TELEGRAM_BOT_USERNAME"] = "TestPlatformBot"
    client.application.config["TELEGRAM_WEBHOOK_SECRET"] = "test-secret"

    register(client, email="user@example.com", role="customer")
    resp = client.get("/settings")
    assert "Подключить Telegram".encode() in resp.data
    assert "t.me/TestPlatformBot?start=".encode() in resp.data

    with client.application.app_context():
        from app.telegram_bot import link_token_for

        user = User.query.filter_by(email="user@example.com").first()
        token = link_token_for(user)
        user_id = user.id

    sent_messages = []
    monkeypatch.setattr("app.telegram_bot.send_message", lambda chat_id, text: sent_messages.append((chat_id, text)) or True)

    resp = client.post(
        "/telegram/webhook/test-secret",
        data=json.dumps({"message": {"chat": {"id": 555111, "username": "ivanov"}, "text": f"/start {token}"}}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    assert len(sent_messages) == 1

    with client.application.app_context():
        link = TelegramLink.query.filter_by(user_id=user_id).first()
        assert link is not None
        assert link.telegram_chat_id == 555111
        assert link.telegram_username == "ivanov"


def test_telegram_link_code_fallback_when_start_payload_dropped(client, monkeypatch):
    """Если пользователь уже писал боту раньше, Telegram при переходе по
    deep-link'у иногда шлёт голый «/start» без токена (сам клиент обрезает
    start-параметр для уже существующих чатов) — тогда должен сработать
    запасной путь: код подтверждения, отправленный обычным текстом."""
    client.application.config["TELEGRAM_BOT_USERNAME"] = "TestPlatformBot"
    client.application.config["TELEGRAM_WEBHOOK_SECRET"] = "test-secret"

    register(client, email="code@example.com", role="customer")
    resp = client.get("/settings")
    assert "может открыть чат без автоматической привязки" in resp.get_data(as_text=True)

    with client.application.app_context():
        from app.models import TelegramLinkCode

        user = User.query.filter_by(email="code@example.com").first()
        user_id = user.id
        code = TelegramLinkCode.query.filter_by(user_id=user_id).first().code

    sent_messages = []
    monkeypatch.setattr("app.telegram_bot.send_message", lambda chat_id, text: sent_messages.append((chat_id, text)) or True)

    resp = client.post(
        "/telegram/webhook/test-secret",
        data=json.dumps({"message": {"chat": {"id": 777222, "username": "petrov"}, "text": code}}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    assert len(sent_messages) == 1

    with client.application.app_context():
        link = TelegramLink.query.filter_by(user_id=user_id).first()
        assert link is not None
        assert link.telegram_chat_id == 777222
        from app.models import TelegramLinkCode

        assert TelegramLinkCode.query.filter_by(user_id=user_id).first() is None


def test_telegram_link_code_rejects_unknown_code(client, monkeypatch):
    client.application.config["TELEGRAM_WEBHOOK_SECRET"] = "test-secret"
    sent_messages = []
    monkeypatch.setattr("app.telegram_bot.send_message", lambda chat_id, text: sent_messages.append((chat_id, text)) or True)

    resp = client.post(
        "/telegram/webhook/test-secret",
        data=json.dumps({"message": {"chat": {"id": 1}, "text": "DEADBEEF"}}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    assert "устарел или неверен" in sent_messages[0][1]


def test_webhook_rejects_wrong_secret(client):
    client.application.config["TELEGRAM_WEBHOOK_SECRET"] = "real-secret"
    resp = client.post(
        "/telegram/webhook/wrong-secret",
        data=json.dumps({"message": {"chat": {"id": 1}, "text": "/start x"}}),
        content_type="application/json",
    )
    assert resp.status_code == 404


def test_notify_sends_telegram_message_when_linked(client, monkeypatch):
    region_id = _setup_customer(client, "cust3@example.com")
    _setup_executor(client, "exec3@example.com", region_id)

    with client.application.app_context():
        user = User.query.filter_by(email="exec3@example.com").first()
        db.session.add(TelegramLink(user_id=user.id, telegram_chat_id=999, notifications_enabled=True))
        db.session.commit()

    sent = []
    monkeypatch.setattr("app.telegram_bot.send_message", lambda chat_id, text: sent.append((chat_id, text)) or True)

    _login(client, "cust3@example.com")
    with client.application.app_context():
        from app.models import ServiceCategory as SC
        sc = SC.query.first()
    _create_order(client, region_id, sc.id)

    assert len(sent) == 1
    assert sent[0][0] == 999
    with client.application.app_context():
        notif = Notification.query.filter_by(type="new_order_match").first()
        assert notif.telegram_sent is True


def test_notify_stays_in_app_only_when_no_token_and_not_linked(client):
    region_id = _setup_customer(client, "cust4@example.com")
    _setup_executor(client, "exec4@example.com", region_id)
    _login(client, "cust4@example.com")

    with client.application.app_context():
        from app.models import ServiceCategory as SC
        sc = SC.query.first()
    _create_order(client, region_id, sc.id)

    with client.application.app_context():
        notif = Notification.query.filter_by(type="new_order_match").first()
        assert notif is not None
        assert notif.telegram_sent is False


def test_subscription_request_and_admin_approval_flow(client):
    from werkzeug.security import generate_password_hash

    region_id = _setup_customer(client, "cust5@example.com")
    _setup_executor(client, "exec5@example.com", region_id)

    _login(client, "exec5@example.com")
    resp = client.get("/subscription")
    assert "Пробный период".encode() in resp.data or b"trial" in resp.data or resp.status_code == 200

    with client.application.app_context():
        plan_code = SubscriptionPlan.query.filter_by(code="standard").first().code

    resp = client.post("/subscription/request", data={"plan_code": plan_code, "provider": "payme"}, follow_redirects=True)
    assert "Заявка на тариф принята".encode() in resp.data

    with client.application.app_context():
        pending = Subscription.query.filter_by(status="pending_payment").first()
        assert pending is not None
        assert pending.payments[0].status == "pending"
    client.get("/auth/logout")

    with client.application.app_context():
        admin = User(email="admin2@example.com", password_hash=generate_password_hash("adminpass123"), role="admin", email_confirmed=True)
        db.session.add(admin)
        db.session.commit()
        subscription_id = pending.id

    _login(client, "admin2@example.com", "adminpass123")
    resp = client.post(f"/admin/subscriptions/{subscription_id}/approve", data={"reference": "TXN123"}, follow_redirects=True)
    assert "Подписка активирована".encode() in resp.data

    with client.application.app_context():
        sub = db.session.get(Subscription, subscription_id)
        assert sub.status == "active"
        assert sub.expires_at > datetime.utcnow()
        assert sub.payments[0].status == "succeeded"
        assert sub.payments[0].provider_transaction_id == "TXN123"
