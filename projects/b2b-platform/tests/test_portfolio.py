from app import db
from app.models import Order, PortfolioMedia, User

from tests.conftest import register
from tests.test_orders import _create_order, _login, _setup_customer, _setup_executor


def test_add_and_delete_video_portfolio_item(client):
    register(client, email="exec1@example.com", role="executor")
    resp = client.post(
        "/profile/portfolio/add",
        data={"media_type": "video", "video_url": "https://youtube.com/watch?v=abc", "caption": "Наш цех"},
        follow_redirects=True,
    )
    assert "Добавлено в портфолио".encode() in resp.data

    with client.application.app_context():
        user = User.query.filter_by(email="exec1@example.com").first()
        item = PortfolioMedia.query.filter_by(user_id=user.id).first()
        assert item is not None
        assert item.media_type == "video"
        assert item.caption == "Наш цех"
        item_id = item.id

    resp = client.post(f"/profile/portfolio/{item_id}/delete", follow_redirects=True)
    assert "Удалено из портфолио".encode() in resp.data
    with client.application.app_context():
        assert db.session.get(PortfolioMedia, item_id) is None


def test_add_video_requires_url(client):
    register(client, email="exec2@example.com", role="executor")
    resp = client.post("/profile/portfolio/add", data={"media_type": "video", "video_url": ""}, follow_redirects=True)
    assert "Укажите ссылку на видео".encode() in resp.data


def test_cannot_delete_other_users_portfolio_item(client):
    register(client, email="exec3@example.com", role="executor")
    client.post(
        "/profile/portfolio/add", data={"media_type": "video", "video_url": "https://youtube.com/x"},
        follow_redirects=True,
    )
    with client.application.app_context():
        item_id = PortfolioMedia.query.first().id
    client.get("/auth/logout")

    register(client, email="exec4@example.com", role="executor")
    resp = client.post(f"/profile/portfolio/{item_id}/delete")
    assert resp.status_code == 404


def test_executor_public_profile_hides_contact_before_deal_and_shows_after(client):
    region_id = _setup_customer(client, "cust@example.com")
    service_id, _ = _setup_executor(client, "exec@example.com", region_id)

    with client.application.app_context():
        executor_user_id = User.query.filter_by(email="exec@example.com").first().id

    _login(client, "cust@example.com")
    resp = client.get(f"/profile/executor/{executor_user_id}")
    assert resp.status_code == 200
    assert "открываются после того, как вы заключите сделку".encode() in resp.data

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
    client.get("/auth/logout")

    _login(client, "cust@example.com")
    with client.application.app_context():
        bid_id = Order.query.get(order_id).bids[0].id
    client.post(f"/orders/{order_id}/assign/{bid_id}", follow_redirects=True)

    resp = client.get(f"/profile/executor/{executor_user_id}")
    assert "Контакты".encode() in resp.data
    assert "открываются после того".encode() not in resp.data


def test_customer_public_profile_visible_to_executor_with_portfolio_link_from_order(client):
    region_id = _setup_customer(client, "cust2@example.com")
    service_id, _ = _setup_executor(client, "exec5@example.com", region_id)

    with client.application.app_context():
        customer_user_id = User.query.filter_by(email="cust2@example.com").first().id

    _login(client, "cust2@example.com")
    _create_order(client, region_id, service_id)
    with client.application.app_context():
        order_id = Order.query.first().id
    client.get("/auth/logout")

    _login(client, "exec5@example.com")
    resp = client.get(f"/orders/{order_id}")
    assert "Профиль и портфолио заказчика".encode() in resp.data

    resp = client.get(f"/profile/customer/{customer_user_id}")
    assert resp.status_code == 200
    assert "открываются после того".encode() in resp.data
