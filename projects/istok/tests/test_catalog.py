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


def test_catalog_sort_by_volume_column(client):
    resp = client.get("/catalog/?sort=volume&dir=desc")
    assert resp.status_code == 200
    # "Тестовая вода" (1.5 л) должна идти раньше "Тестовая вода 2" (1.0 л)
    assert resp.data.index("Тестовая вода</a>".encode()) < resp.data.index("Тестовая вода 2".encode())


def test_catalog_sort_invalid_falls_back_to_default(client):
    resp = client.get("/catalog/?sort=not-a-column&dir=sideways")
    assert resp.status_code == 200


def _register_and_confirm(client, app, email):
    from itsdangerous import URLSafeTimedSerializer
    from app.routes.auth import CONFIRM_SALT

    client.post(
        "/auth/register",
        data={"email": email, "password": "password123", "password2": "password123"},
    )
    with app.app_context():
        token = URLSafeTimedSerializer(app.config["SECRET_KEY"]).dumps(email, salt=CONFIRM_SALT)
    client.get(f"/auth/confirm/{token}")


def test_add_water_brand_blocked_until_confirmed(client):
    client.post(
        "/auth/register",
        data={"email": "unconfirmedbrand@user.example", "password": "password123", "password2": "password123"},
    )
    resp = client.post(
        "/catalog/add",
        data={"name": "Спам-вода", "water_type": "питьевая", "volume_l": "1", "price": "10"},
        follow_redirects=True,
    )
    assert "подтвердите email".encode() in resp.data

    from app.models import WaterBrand

    assert WaterBrand.query.filter_by(name="Спам-вода").first() is None


def test_add_water_brand_after_confirmation(client, app):
    _register_and_confirm(client, app, "brandowner@user.example")

    resp = client.post(
        "/catalog/add",
        data={
            "name": "Новая тестовая марка",
            "water_type": "питьевая негазированная",
            "volume_l": "1.5",
            "price": "42",
            "currency": "KZT",
            "country": "Казахстан",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "не проверено".encode() in resp.data

    with app.app_context():
        from app.models import WaterBrand

        brand = WaterBrand.query.filter_by(name="Новая тестовая марка").first()
        assert brand is not None
        assert brand.verified is False
        assert brand.added_by_user_id is not None
        assert brand.currency == "KZT"
        assert brand.slug

    resp = client.get("/catalog/")
    assert "Новая тестовая марка".encode() in resp.data
