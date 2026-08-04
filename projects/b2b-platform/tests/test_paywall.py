from tests.conftest import register


def test_anonymous_cannot_reach_customer_profile(client):
    resp = client.get("/profile/customer", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["Location"].startswith("/") or "auth_required=1" in resp.headers["Location"]
    assert "auth_required=1" in resp.headers["Location"]


def test_anonymous_cannot_reach_executor_profile(client):
    resp = client.get("/profile/executor", follow_redirects=False)
    assert resp.status_code == 302
    assert "auth_required=1" in resp.headers["Location"]


def test_home_page_is_public(client):
    resp = client.get("/")
    assert resp.status_code == 200


def test_wrong_role_gets_forbidden(client):
    register(client, email="cust@example.com", role="customer")
    resp = client.get("/profile/executor")
    assert resp.status_code == 403


def test_authenticated_customer_reaches_own_profile(client):
    register(client, email="cust2@example.com", role="customer")
    resp = client.get("/profile/customer")
    assert resp.status_code == 200
