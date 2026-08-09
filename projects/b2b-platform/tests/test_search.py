from app.models import ListingCategory, Region

from tests.conftest import register
from tests.test_orders import _login, _setup_customer, _setup_executor


def test_search_requires_auth(client):
    resp = client.get("/search?q=станок", follow_redirects=False)
    assert resp.status_code == 302
    assert "auth_required=1" in resp.headers["Location"]


def test_search_partial_match_finds_listing(client):
    region_id = _setup_customer(client, "sellersearch@example.com")
    with client.application.app_context():
        category_id = ListingCategory.query.first().id

    register(client, email="sellersearch2@example.com", role="customer")
    client.post(
        "/marketplace/new",
        data={
            "listing_intent": "sell", "category_id": str(category_id), "title": "Токарный станок 1К62",
            "description": "Рабочее состояние", "condition": "used", "region_id": str(region_id),
        },
        follow_redirects=True,
    )

    resp = client.get("/search?q=токарный&mode=partial")
    assert "Токарный станок 1К62".encode() in resp.data


def test_search_exact_mode_requires_full_title_match(client):
    region_id = _setup_customer(client, "sellersearch3@example.com")
    with client.application.app_context():
        category_id = ListingCategory.query.first().id

    register(client, email="sellersearch4@example.com", role="customer")
    client.post(
        "/marketplace/new",
        data={
            "listing_intent": "sell", "category_id": str(category_id), "title": "Токарный станок 1К62",
            "description": "Рабочее состояние", "condition": "used", "region_id": str(region_id),
        },
        follow_redirects=True,
    )

    partial_resp = client.get("/search?q=токарный&mode=exact")
    assert "Токарный станок 1К62".encode() not in partial_resp.data

    exact_resp = client.get("/search?q=Токарный станок 1К62&mode=exact")
    assert "Токарный станок 1К62".encode() in exact_resp.data


def test_search_finds_executor_by_display_name(client):
    region_id = _setup_customer(client, "custforsearch@example.com")
    _setup_executor(client, "execforsearch@example.com", region_id)

    _login(client, "custforsearch@example.com")
    resp = client.get("/search?q=execforsearch&mode=partial")
    assert "Цех execforsearch@example.com".encode() in resp.data


def test_search_with_no_query_shows_no_results_sections(client):
    _setup_customer(client, "emptysearch@example.com")
    register(client, email="emptysearch2@example.com", role="customer")
    resp = client.get("/search")
    assert resp.status_code == 200


def test_search_percent_in_query_does_not_match_everything(client):
    """Проверка экранирования LIKE-спецсимволов — запрос "%​" не должен
    находить вообще всё подряд из-за неэкранированного wildcard'а."""
    region_id = _setup_customer(client, "wildcardsearch@example.com")
    with client.application.app_context():
        category_id = ListingCategory.query.first().id

    register(client, email="wildcardsearch2@example.com", role="customer")
    client.post(
        "/marketplace/new",
        data={
            "listing_intent": "sell", "category_id": str(category_id), "title": "Фреза концевая",
            "description": "Новая", "condition": "new", "region_id": str(region_id),
        },
        follow_redirects=True,
    )

    resp = client.get("/search?q=%25&mode=partial")
    assert "Фреза концевая".encode() not in resp.data
