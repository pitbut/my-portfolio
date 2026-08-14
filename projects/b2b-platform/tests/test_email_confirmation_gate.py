"""Гейт «подтверди email, чтобы выполнить действие» — точечный, не на весь
сайт: смотреть каталог, искать и заполнять свою анкету можно и без
подтверждения, а вот создать заявку, сделать ставку, написать сообщение,
опубликовать объявление и т.п. — нельзя, пока не перейдёшь по ссылке из
письма (или пока email не подтверждён Google-ом при входе через OAuth)."""
from datetime import datetime

from werkzeug.security import generate_password_hash

from app import db
from app.models import Region, ServiceCategory, User

from tests.conftest import register


def _setup_unconfirmed_customer(client, email="unconfirmed@example.com"):
    register(client, email=email, role="customer", confirm_email=False)
    with client.application.app_context():
        region_id = Region.query.first().id
    client.post(
        "/profile/customer",
        data={
            "kind": "company", "display_name": "Завод Б", "region_id": str(region_id),
            "address_text": "Ташкент, промзона", "latitude": "41.30", "longitude": "69.25",
        },
        follow_redirects=True,
    )
    return region_id


def test_unconfirmed_customer_can_browse_and_fill_profile(client):
    """Точечный гейт: каталог/поиск/анкета остаются открытыми до подтверждения."""
    _setup_unconfirmed_customer(client, "browse@example.com")

    for path in ("/marketplace", "/materials", "/jobs", "/search", "/profile/customer"):
        resp = client.get(path)
        assert resp.status_code == 200, f"{path} должен быть открыт до подтверждения email"


def test_unconfirmed_customer_cannot_create_order(client):
    region_id = _setup_unconfirmed_customer(client, "noorder@example.com")
    with client.application.app_context():
        service_id = ServiceCategory.query.first().id

    resp = client.post(
        "/orders/new",
        data={
            "title": "Токарная обточка вала", "description": "Нужно выточить вал",
            "order_type": "manufacturing", "service_category_id": str(service_id),
            "region_id": str(region_id), "address_text": "Ташкент", "auction_hours": "48",
        },
        follow_redirects=True,
    )
    assert "Подтвердите email".encode() in resp.data

    with client.application.app_context():
        from app.models import Order

        assert Order.query.filter_by(title="Токарная обточка вала").first() is None


def test_confirmed_customer_can_create_order(client):
    """Обычный (подтверждённый через тестовый хелпер) путь продолжает работать."""
    register(client, email="confirmedcust@example.com", role="customer")
    with client.application.app_context():
        region_id = Region.query.first().id
        service_id = ServiceCategory.query.first().id
    client.post(
        "/profile/customer",
        data={
            "kind": "company", "display_name": "Завод В", "region_id": str(region_id),
            "address_text": "Ташкент, промзона", "latitude": "41.30", "longitude": "69.25",
        },
        follow_redirects=True,
    )

    resp = client.post(
        "/orders/new",
        data={
            "title": "Фрезеровка детали", "description": "Нужна фрезеровка",
            "order_type": "manufacturing", "service_category_id": str(service_id),
            "region_id": str(region_id), "address_text": "Ташкент", "auction_hours": "48",
        },
        follow_redirects=True,
    )
    assert "Подтвердите email".encode() not in resp.data

    with client.application.app_context():
        from app.models import Order

        assert Order.query.filter_by(title="Фрезеровка детали").first() is not None


def test_clicking_real_confirmation_link_unblocks_action(client):
    """(в) — переход по реальной ссылке подтверждения снимает ограничение."""
    region_id = _setup_unconfirmed_customer(client, "willconfirm@example.com")
    with client.application.app_context():
        service_id = ServiceCategory.query.first().id

    order_data = {
        "title": "Заявка до подтверждения", "description": "Описание",
        "order_type": "manufacturing", "service_category_id": str(service_id),
        "region_id": str(region_id), "address_text": "Ташкент", "auction_hours": "48",
    }

    blocked = client.post("/orders/new", data=order_data, follow_redirects=True)
    assert "Подтвердите email".encode() in blocked.data

    from app.routes.auth import confirm_url_for

    with client.application.test_request_context():
        with client.application.app_context():
            user = User.query.filter_by(email="willconfirm@example.com").first()
            url = confirm_url_for(user)
    path = url.split("localhost", 1)[-1] if "localhost" in url else url
    resp = client.get(path, follow_redirects=True)
    assert resp.status_code == 200

    with client.application.app_context():
        assert User.query.filter_by(email="willconfirm@example.com").first().email_confirmed is True

    allowed = client.post(
        "/orders/new",
        data={**order_data, "title": "Заявка после подтверждения"},
        follow_redirects=True,
    )
    assert "Подтвердите email".encode() not in allowed.data
    with client.application.app_context():
        from app.models import Order

        assert Order.query.filter_by(title="Заявка после подтверждения").first() is not None


def test_google_oauth_style_user_bypasses_gate_immediately(client):
    """(г) — пользователь, вошедший через Google (email_confirmed выставлен
    сразу при создании аккаунта, см. google_callback), не должен упираться в
    гейт вообще — Google уже подтвердил email за него."""
    with client.application.app_context():
        user = User(
            email="viagoogle@example.com", google_sub="fake-google-sub-1",
            role="customer", email_confirmed=True, confirmed_at=datetime.utcnow(),
        )
        db.session.add(user)
        db.session.commit()
        region_id = Region.query.first().id
        service_id = ServiceCategory.query.first().id

    with client.session_transaction() as sess:
        with client.application.app_context():
            user_id = User.query.filter_by(email="viagoogle@example.com").first().id
        sess["_user_id"] = str(user_id)
        sess["_fresh"] = True

    client.post(
        "/profile/customer",
        data={
            "kind": "company", "display_name": "Завод Google", "region_id": str(region_id),
            "address_text": "Ташкент", "latitude": "41.30", "longitude": "69.25",
        },
        follow_redirects=True,
    )

    resp = client.post(
        "/orders/new",
        data={
            "title": "Заявка через Google-аккаунт", "description": "Описание",
            "order_type": "manufacturing", "service_category_id": str(service_id),
            "region_id": str(region_id), "address_text": "Ташкент", "auction_hours": "48",
        },
        follow_redirects=True,
    )
    assert "Подтвердите email".encode() not in resp.data
    with client.application.app_context():
        from app.models import Order

        assert Order.query.filter_by(title="Заявка через Google-аккаунт").first() is not None


def test_unconfirmed_executor_cannot_message_in_chat(client):
    """Проверка гейта на другой блюпринт (chat), не только orders — сообщения
    в чате тоже требуют подтверждённый email."""
    register(client, email="chatunconf@example.com", role="customer", confirm_email=False)
    other_id_holder = {}
    with client.application.app_context():
        from app.models import User as U

        other = U(
            email="chatpeer@example.com", password_hash=generate_password_hash("password123"),
            role="executor", email_confirmed=True,
        )
        db.session.add(other)
        db.session.commit()
        other_id_holder["id"] = other.id

    resp = client.post(
        f"/messages/u/{other_id_holder['id']}",
        data={"body": "Привет, есть вопрос по заявке"},
        follow_redirects=True,
    )
    assert "Подтвердите email".encode() in resp.data

    with client.application.app_context():
        from app.models import Message

        assert Message.query.filter_by(body="Привет, есть вопрос по заявке").first() is None
