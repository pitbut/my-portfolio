from app.models import Region

from tests.conftest import register
from tests.test_orders import _setup_customer, _setup_executor, _login


def test_map_requires_auth(client):
    resp = client.get("/map", follow_redirects=False)
    assert resp.status_code == 302
    assert "auth_required=1" in resp.headers["Location"]


def test_executors_json_excludes_incomplete_profiles(client):
    region_id = _setup_customer(client, "cust@example.com")
    _login(client, "cust@example.com")

    # исполнитель без техвозможностей не должен попасть на карту
    register(client, email="incomplete@example.com", role="executor")
    client.post(
        "/profile/executor",
        data={"org_type": "master", "display_name": "Мастер без парка", "region_id": str(region_id), "address_text": "тут", "latitude": "41.3", "longitude": "69.3"},
        follow_redirects=True,
    )
    client.get("/auth/logout")

    _login(client, "cust@example.com")
    resp = client.get("/map/executors.json")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_executors_json_includes_complete_profile_and_filters(client):
    region_id = _setup_customer(client, "cust2@example.com")
    service_id, _ = _setup_executor(client, "full@example.com", region_id)

    _login(client, "cust2@example.com")
    resp = client.get("/map/executors.json")
    data = resp.get_json()
    assert len(data) == 1
    assert data[0]["name"].startswith("Цех")

    resp = client.get(f"/map/executors.json?service_category_id={service_id}")
    assert len(resp.get_json()) == 1

    resp = client.get("/map/executors.json?org_type=zavod")
    assert resp.get_json() == []


def test_nearby_json_sorts_by_distance(client):
    region_id = _setup_customer(client, "cust3@example.com")
    _setup_executor(client, "near@example.com", region_id)  # lat 41.31, lng 69.26 в helper'е

    _login(client, "cust3@example.com")
    resp = client.get("/map/nearby.json?lat=41.30&lng=69.25&radius_km=50")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 1
    assert "distance_km" in data[0]

    resp = client.get("/map/nearby.json?lat=55.75&lng=37.61&radius_km=50")  # далеко (для примера, Москва)
    assert resp.get_json() == []
