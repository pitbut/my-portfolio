import io
from unittest.mock import MagicMock, patch

from itsdangerous import URLSafeTimedSerializer

from app.models import EditSuggestion, Equipment, Review, Supplier
from app.routes.auth import CONFIRM_SALT


def _confirm_token(app, email):
    with app.app_context():
        serializer = URLSafeTimedSerializer(app.config["SECRET_KEY"])
        return serializer.dumps(email, salt=CONFIRM_SALT)


def _register_and_confirm(client, app, email):
    client.post(
        "/auth/register",
        data={"email": email, "password": "password123", "password2": "password123"},
    )
    token = _confirm_token(app, email)
    client.get(f"/auth/confirm/{token}")


def _fake_photo(name="photo.jpg"):
    return (io.BytesIO(b"fake-bytes"), name)


def _mock_imgbb_success(url="https://i.ibb.co/abc/photo.jpg"):
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.json.return_value = {"success": True, "data": {"url": url}}
    return mock_response


def test_equipment_add_with_photo(client, app):
    app.config["IMGBB_API_KEY"] = "test-key"
    _register_and_confirm(client, app, "photoeq@user.example")

    with patch("app.photos.requests.post", return_value=_mock_imgbb_success()):
        resp = client.post(
            "/equipment/add",
            data={
                "name": "Фото-фильтр",
                "category": "Фильтр",
                "description": "d",
                "photo": _fake_photo(),
            },
            content_type="multipart/form-data",
            follow_redirects=True,
        )
    assert resp.status_code == 200

    with app.app_context():
        item = Equipment.query.filter_by(name="Фото-фильтр").first()
        assert item.image_url == "https://i.ibb.co/abc/photo.jpg"


def test_add_supplier_with_photo(client, app):
    app.config["IMGBB_API_KEY"] = "test-key"
    _register_and_confirm(client, app, "photosup@user.example")

    with patch("app.photos.requests.post", return_value=_mock_imgbb_success()):
        resp = client.post(
            "/catalog/test-water/add-supplier",
            data={"name": "Фото-склад", "address": "ул. Тест, 1", "photo": _fake_photo()},
            content_type="multipart/form-data",
            follow_redirects=True,
        )
    assert resp.status_code == 200

    with app.app_context():
        supplier = Supplier.query.filter_by(name="Фото-склад").first()
        assert supplier.image_url == "https://i.ibb.co/abc/photo.jpg"


def test_review_with_photo(client, app):
    app.config["IMGBB_API_KEY"] = "test-key"
    with app.app_context():
        item_id = Equipment.query.filter_by(slug="test-filter").first().id

    with patch("app.photos.requests.post", return_value=_mock_imgbb_success()):
        resp = client.post(
            f"/reviews/equipment/{item_id}",
            data={"rating": "5", "body": "С фото.", "photo": _fake_photo()},
            content_type="multipart/form-data",
            follow_redirects=True,
        )
    assert resp.status_code == 200

    with app.app_context():
        review = Review.query.filter_by(body="С фото.").first()
        assert review.image_url == "https://i.ibb.co/abc/photo.jpg"


def test_suggest_image_url_with_photo(client, app):
    app.config["IMGBB_API_KEY"] = "test-key"

    with patch("app.photos.requests.post", return_value=_mock_imgbb_success()):
        resp = client.post(
            "/sacred/test-source/suggest",
            data={"field_name": "image_url", "photo": _fake_photo()},
            content_type="multipart/form-data",
            follow_redirects=True,
        )
    assert resp.status_code == 200

    with app.app_context():
        suggestion = EditSuggestion.query.filter_by(field_name="image_url").first()
        assert suggestion is not None
        assert suggestion.proposed_value == "https://i.ibb.co/abc/photo.jpg"


def test_suggest_image_url_without_photo_or_text_fails(client, app):
    resp = client.post(
        "/sacred/test-source/suggest",
        data={"field_name": "image_url"},
        follow_redirects=True,
    )
    assert "Опишите, что предлагаете изменить".encode() in resp.data

    with app.app_context():
        assert EditSuggestion.query.filter_by(field_name="image_url").count() == 0


def test_suggest_image_url_manual_link_fallback(client, app):
    """Без IMGBB_API_KEY (и без файла) можно просто вставить ссылку текстом."""
    resp = client.post(
        "/sacred/test-source/suggest",
        data={"field_name": "image_url", "proposed_value": "https://example.com/photo.jpg"},
        follow_redirects=True,
    )
    assert resp.status_code == 200

    with app.app_context():
        suggestion = EditSuggestion.query.filter_by(field_name="image_url").first()
        assert suggestion is not None
        assert suggestion.proposed_value == "https://example.com/photo.jpg"
