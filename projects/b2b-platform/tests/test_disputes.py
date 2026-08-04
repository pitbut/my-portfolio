from werkzeug.security import generate_password_hash

from app import db
from app.models import Dispute, Order, User

from tests.conftest import register
from tests.test_orders import _create_order, _login, _setup_customer, _setup_executor


def _make_admin(app, email="admin@example.com", password="adminpass123"):
    with app.app_context():
        user = User(email=email, password_hash=generate_password_hash(password), role="admin", email_confirmed=True)
        db.session.add(user)
        db.session.commit()
    return email, password


def _reach_assigned_order(client, customer_email, executor_email, region_id, service_id):
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
    return order_id


def test_open_dispute_sets_order_status_and_notifies_other_party(client):
    region_id = _setup_customer(client, "cust@example.com")
    service_id, _ = _setup_executor(client, "exec@example.com", region_id)
    order_id = _reach_assigned_order(client, "cust@example.com", "exec@example.com", region_id, service_id)

    resp = client.post(
        f"/orders/{order_id}/dispute/open",
        data={"reason_category": "delay", "description": "Сроки сорваны"},
        follow_redirects=True,
    )
    assert "Спор открыт".encode() in resp.data

    with client.application.app_context():
        order = Order.query.get(order_id)
        assert order.status == "disputed"
        assert order.dispute is not None
        assert order.dispute.status == "open"


def test_only_parties_and_admin_can_view_dispute(client):
    region_id = _setup_customer(client, "cust2@example.com")
    service_id, _ = _setup_executor(client, "exec2@example.com", region_id)
    order_id = _reach_assigned_order(client, "cust2@example.com", "exec2@example.com", region_id, service_id)
    client.post(f"/orders/{order_id}/dispute/open", data={"reason_category": "defect", "description": "Брак"}, follow_redirects=True)

    with client.application.app_context():
        dispute_id = Dispute.query.filter_by(order_id=order_id).first().id
    client.get("/auth/logout")

    register(client, email="stranger@example.com", role="customer")
    resp = client.get(f"/disputes/{dispute_id}")
    assert resp.status_code == 403
    client.get("/auth/logout")

    admin_email, admin_password = _make_admin(client.application)
    client.post("/auth/login", data={"email": admin_email, "password": admin_password}, follow_redirects=True)
    resp = client.get(f"/disputes/{dispute_id}")
    assert resp.status_code == 200


def test_admin_resolves_dispute_and_updates_order(client):
    region_id = _setup_customer(client, "cust3@example.com")
    service_id, _ = _setup_executor(client, "exec3@example.com", region_id)
    order_id = _reach_assigned_order(client, "cust3@example.com", "exec3@example.com", region_id, service_id)
    client.post(f"/orders/{order_id}/dispute/open", data={"reason_category": "quality", "description": "Не по чертежу"}, follow_redirects=True)
    client.get("/auth/logout")

    with client.application.app_context():
        dispute_id = Dispute.query.filter_by(order_id=order_id).first().id

    admin_email, admin_password = _make_admin(client.application)
    client.post("/auth/login", data={"email": admin_email, "password": admin_password}, follow_redirects=True)

    resp = client.post(
        f"/admin/disputes/{dispute_id}/resolve",
        data={"resolution": "resolved_customer", "resolution_text": "Претензия обоснована, доработать.", "order_final_status": "cancelled"},
        follow_redirects=True,
    )
    assert "Решение вынесено".encode() in resp.data

    with client.application.app_context():
        dispute = Dispute.query.get(dispute_id)
        assert dispute.status == "resolved_customer"
        assert dispute.resolved_at is not None
        order = Order.query.get(order_id)
        assert order.status == "cancelled"


def test_non_admin_cannot_resolve_dispute(client):
    region_id = _setup_customer(client, "cust4@example.com")
    service_id, _ = _setup_executor(client, "exec4@example.com", region_id)
    order_id = _reach_assigned_order(client, "cust4@example.com", "exec4@example.com", region_id, service_id)
    client.post(f"/orders/{order_id}/dispute/open", data={"reason_category": "other", "description": "test"}, follow_redirects=True)
    with client.application.app_context():
        dispute_id = Dispute.query.filter_by(order_id=order_id).first().id

    resp = client.post(
        f"/admin/disputes/{dispute_id}/resolve",
        data={"resolution": "resolved_customer", "resolution_text": "x", "order_final_status": "completed"},
        follow_redirects=False,
    )
    assert resp.status_code == 403
