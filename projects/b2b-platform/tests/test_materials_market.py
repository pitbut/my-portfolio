from app.models import Listing, Material, MaterialForm, MaterialListing, Notification, Region, User

from tests.conftest import register


def _login(client, email, password="password123"):
    client.post("/auth/login", data={"email": email, "password": password}, follow_redirects=True)


def test_materials_require_auth(client):
    resp = client.get("/materials", follow_redirects=False)
    assert resp.status_code == 302
    assert "auth_required=1" in resp.headers["Location"]


def test_create_and_browse_material_listing(client):
    register(client, email="seller@example.com", role="customer")
    with client.application.app_context():
        material_id = Material.query.first().id
        form_id = MaterialForm.query.first().id
        region_id = Region.query.first().id

    resp = client.post(
        "/materials/new",
        data={
            "listing_intent": "sell", "material_id": str(material_id), "form_id": str(form_id),
            "title": "Лист стали 3мм, 500 кг", "description": "Остаток с производства",
            "quantity": "500", "unit": "kg", "price": "9000000", "currency": "UZS",
            "region_id": str(region_id),
        },
        follow_redirects=True,
    )
    assert "опубликовано".encode() in resp.data
    client.get("/auth/logout")

    register(client, email="buyer@example.com", role="executor")
    resp = client.get("/materials")
    assert "Лист стали 3мм, 500 кг".encode() in resp.data

    resp = client.get(f"/materials?material_id={material_id}")
    assert "Лист стали 3мм, 500 кг".encode() in resp.data


def test_respond_notifies_author_and_owner_cannot_respond_to_own(client):
    register(client, email="seller2@example.com", role="customer")
    with client.application.app_context():
        material_id = Material.query.first().id
        region_id = Region.query.first().id
    client.post(
        "/materials/new",
        data={"listing_intent": "buy", "material_id": str(material_id), "title": "Куплю трубу",
              "description": "Нужна труба 100 мм", "region_id": str(region_id)},
        follow_redirects=True,
    )
    with client.application.app_context():
        listing_id = MaterialListing.query.first().id

    resp = client.post(f"/materials/{listing_id}/respond", data={"message": "себе"}, follow_redirects=True)
    assert "Нельзя откликнуться на собственное".encode() in resp.data
    client.get("/auth/logout")

    register(client, email="buyer2@example.com", role="executor")
    resp = client.post(f"/materials/{listing_id}/respond", data={"message": "Есть труба, торг", "offered_price": "3000000"}, follow_redirects=True)
    assert "Отклик отправлен".encode() in resp.data

    with client.application.app_context():
        seller = User.query.filter_by(email="seller2@example.com").first()
        notif = Notification.query.filter_by(user_id=seller.id, type="material_response").first()
        assert notif is not None


def test_materials_and_equipment_listings_are_independent(client):
    """Барахолка (Listing) и материалы (MaterialListing) — разные таблицы,
    объявление одного вида не должно просачиваться в выдачу другого."""
    register(client, email="seller3@example.com", role="customer")
    with client.application.app_context():
        material_id = Material.query.first().id
        region_id = Region.query.first().id
    client.post(
        "/materials/new",
        data={"listing_intent": "sell", "material_id": str(material_id), "title": "Пруток алюминиевый",
              "description": "10 метров", "region_id": str(region_id)},
        follow_redirects=True,
    )

    with client.application.app_context():
        assert MaterialListing.query.count() == 1
        assert Listing.query.count() == 0

    resp = client.get("/marketplace")
    assert "Пруток алюминиевый".encode() not in resp.data
