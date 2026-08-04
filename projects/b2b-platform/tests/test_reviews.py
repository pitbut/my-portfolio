from app.models import ExecutorProfile, Order, Review

from tests.conftest import register
from tests.test_orders import _create_order, _login, _setup_customer, _setup_executor


def _complete_order(client, customer_email, executor_email, region_id, service_id):
    _login(client, customer_email)
    _create_order(client, region_id, service_id)
    with client.application.app_context():
        order_id = Order.query.first().id
    client.get("/auth/logout")

    _login(client, executor_email)
    client.post(f"/orders/{order_id}/bid", data={"price": "100000", "lead_time_days": "3"}, follow_redirects=True)
    with client.application.app_context():
        bid_id = Order.query.get(order_id).bids[0].id
    client.get("/auth/logout")

    _login(client, customer_email)
    client.post(f"/orders/{order_id}/assign/{bid_id}", follow_redirects=True)
    client.get("/auth/logout")

    _login(client, executor_email)
    client.post(f"/orders/{order_id}/start", follow_redirects=True)
    client.get("/auth/logout")

    _login(client, customer_email)
    client.post(f"/orders/{order_id}/complete", follow_redirects=True)
    return order_id


def test_review_hidden_until_both_sides_submit(client):
    region_id = _setup_customer(client, "cust@example.com")
    service_id, _ = _setup_executor(client, "exec@example.com", region_id)
    order_id = _complete_order(client, "cust@example.com", "exec@example.com", region_id, service_id)

    # заказчик уже залогинен после _complete_order
    resp = client.post(f"/orders/{order_id}/review", data={"rating": "5", "comment": "Отлично"}, follow_redirects=True)
    assert "будет опубликован".encode() in resp.data

    with client.application.app_context():
        reviews = Review.query.filter_by(order_id=order_id).all()
        assert len(reviews) == 1
        assert reviews[0].is_published is False

    client.get("/auth/logout")
    _login(client, "exec@example.com")
    resp = client.post(f"/orders/{order_id}/review", data={"rating": "4", "comment": "Хороший заказчик"}, follow_redirects=True)
    assert "Оба отзыва опубликованы".encode() in resp.data

    with client.application.app_context():
        reviews = Review.query.filter_by(order_id=order_id).all()
        assert len(reviews) == 2
        assert all(r.is_published for r in reviews)

        exec_profile = ExecutorProfile.query.join(ExecutorProfile.user).filter_by(email="exec@example.com").first()
        assert float(exec_profile.rating_avg) == 5.0
        assert exec_profile.reviews_count == 1


def test_cannot_review_before_completion(client):
    region_id = _setup_customer(client, "cust2@example.com")
    service_id, _ = _setup_executor(client, "exec2@example.com", region_id)
    _login(client, "cust2@example.com")
    _create_order(client, region_id, service_id)
    with client.application.app_context():
        order_id = Order.query.first().id

    resp = client.post(f"/orders/{order_id}/review", data={"rating": "5"}, follow_redirects=True)
    assert "только после завершения".encode() in resp.data


def test_stranger_cannot_review_order(client):
    region_id = _setup_customer(client, "cust3@example.com")
    service_id, _ = _setup_executor(client, "exec3@example.com", region_id)
    order_id = _complete_order(client, "cust3@example.com", "exec3@example.com", region_id, service_id)
    client.get("/auth/logout")

    register(client, email="stranger@example.com", role="customer")
    resp = client.post(f"/orders/{order_id}/review", data={"rating": "5"}, follow_redirects=False)
    assert resp.status_code == 403
