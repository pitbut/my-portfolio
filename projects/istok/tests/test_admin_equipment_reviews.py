from app import db
from app.models import Equipment, Review


def _login_admin(client, app):
    return client.post("/admin/login", data={"password": app.config["ADMIN_PASSWORD"]}, follow_redirects=True)


def test_admin_equipment_requires_login(client):
    resp = client.get("/admin/equipment")
    assert resp.status_code == 302
    assert "/admin/login" in resp.headers["Location"]


def test_admin_can_verify_equipment(client, app):
    with app.app_context():
        item = Equipment.query.filter_by(slug="test-filter").first()
        item.verified = False
        db.session.commit()
        item_id = item.id

    _login_admin(client, app)
    resp = client.post(f"/admin/equipment/{item_id}/verify", follow_redirects=True)
    assert resp.status_code == 200

    detail = client.get("/equipment/test-filter")
    assert ">проверено<".encode() in detail.data


def test_admin_can_delete_equipment(client, app):
    with app.app_context():
        item_id = Equipment.query.filter_by(slug="test-filter").first().id

    _login_admin(client, app)
    resp = client.post(f"/admin/equipment/{item_id}/delete", follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        assert db.session.get(Equipment, item_id) is None


def test_admin_reviews_requires_login(client):
    resp = client.get("/admin/reviews")
    assert resp.status_code == 302
    assert "/admin/login" in resp.headers["Location"]


def test_admin_can_delete_review(client, app):
    with app.app_context():
        item_id = Equipment.query.filter_by(slug="test-filter").first().id

    client.post(f"/reviews/equipment/{item_id}", data={"rating": "5", "body": "Отзыв на удаление."})

    with app.app_context():
        review_id = Review.query.filter_by(body="Отзыв на удаление.").first().id

    _login_admin(client, app)
    resp = client.get("/admin/reviews")
    assert "Отзыв на удаление.".encode() in resp.data

    resp = client.post(f"/admin/reviews/{review_id}/delete", follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        assert db.session.get(Review, review_id) is None
