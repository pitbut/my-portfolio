def test_catalog_index(client):
    resp = client.get("/catalog/")
    assert resp.status_code == 200
    assert "Тестовая вода".encode() in resp.data


def test_catalog_sorting(client):
    resp = client.get("/catalog/?sort=price_desc")
    assert resp.status_code == 200

    resp_invalid = client.get("/catalog/?sort=not-a-real-option")
    assert resp_invalid.status_code == 200


def test_catalog_country_filter(client):
    resp = client.get("/catalog/?country=Узбекистан")
    assert resp.status_code == 200
    assert "Тестовая вода 2".encode() in resp.data
    assert "Тестовая вода</a>".encode() not in resp.data


def test_catalog_shows_currency(client):
    resp = client.get("/catalog/")
    assert "сум".encode() in resp.data
    assert "₽".encode() in resp.data


def test_catalog_shows_average_rating(client, app):
    from app import db
    from app.models import Review, WaterBrand

    with app.app_context():
        brand = WaterBrand.query.filter_by(slug="test-water").first()
        db.session.add(Review(target_type="water_brand", target_id=brand.id, rating=5, body="Отлично!"))
        db.session.add(Review(target_type="water_brand", target_id=brand.id, rating=3, body="Нормально."))
        db.session.commit()

    resp = client.get("/catalog/")
    assert "★ 4.0".encode() in resp.data
