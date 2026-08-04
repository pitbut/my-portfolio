from app.models import ListingCategory, Notification, Region, User

from tests.conftest import register


def _login(client, email, password="password123"):
    client.post("/auth/login", data={"email": email, "password": password}, follow_redirects=True)


def test_marketplace_requires_auth(client):
    resp = client.get("/marketplace", follow_redirects=False)
    assert resp.status_code == 302
    assert "auth_required=1" in resp.headers["Location"]


def test_create_and_browse_listing(client):
    register(client, email="seller@example.com", role="customer")
    with client.application.app_context():
        category_id = ListingCategory.query.first().id
        region_id = Region.query.first().id

    resp = client.post(
        "/marketplace/new",
        data={
            "listing_intent": "sell", "category_id": str(category_id), "title": "Токарный станок 1К62",
            "description": "Рабочее состояние, полный комплект", "condition": "used",
            "price": "15000000", "currency": "UZS", "region_id": str(region_id),
        },
        follow_redirects=True,
    )
    assert "опубликовано".encode() in resp.data
    client.get("/auth/logout")

    register(client, email="buyer@example.com", role="executor")
    resp = client.get("/marketplace")
    assert "Токарный станок 1К62".encode() in resp.data


def test_respond_notifies_author_and_owner_cannot_respond_to_own(client):
    register(client, email="seller2@example.com", role="customer")
    with client.application.app_context():
        category_id = ListingCategory.query.first().id
        region_id = Region.query.first().id
    client.post(
        "/marketplace/new",
        data={"listing_intent": "sell", "category_id": str(category_id), "title": "Фрезерный станок",
              "description": "Продам", "region_id": str(region_id)},
        follow_redirects=True,
    )
    from app.models import Listing
    with client.application.app_context():
        listing_id = Listing.query.first().id

    # владелец не может откликнуться на своё же объявление
    resp = client.post(f"/marketplace/{listing_id}/respond", data={"message": "себе"}, follow_redirects=True)
    assert "Нельзя откликнуться на собственное".encode() in resp.data
    client.get("/auth/logout")

    register(client, email="buyer2@example.com", role="executor")
    resp = client.post(f"/marketplace/{listing_id}/respond", data={"message": "Интересует, торг?", "offered_price": "5000000"}, follow_redirects=True)
    assert "Отклик отправлен".encode() in resp.data

    with client.application.app_context():
        seller = User.query.filter_by(email="seller2@example.com").first()
        notif = Notification.query.filter_by(user_id=seller.id, type="listing_response").first()
        assert notif is not None


def test_only_owner_can_change_status(client):
    register(client, email="seller3@example.com", role="customer")
    with client.application.app_context():
        category_id = ListingCategory.query.first().id
        region_id = Region.query.first().id
    client.post(
        "/marketplace/new",
        data={"listing_intent": "buy", "category_id": str(category_id), "title": "Ищу пресс",
              "description": "Куплю гидравлический пресс", "region_id": str(region_id)},
        follow_redirects=True,
    )
    from app.models import Listing
    with client.application.app_context():
        listing_id = Listing.query.first().id
    client.get("/auth/logout")

    register(client, email="stranger@example.com", role="executor")
    resp = client.post(f"/marketplace/{listing_id}/status", data={"status": "closed"}, follow_redirects=False)
    assert resp.status_code == 404
