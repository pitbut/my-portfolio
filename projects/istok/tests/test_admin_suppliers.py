from app import db
from app.models import Supplier


def _login_admin(client, app):
    return client.post("/admin/login", data={"password": app.config["ADMIN_PASSWORD"]}, follow_redirects=True)


def test_admin_suppliers_requires_login(client):
    resp = client.get("/admin/suppliers")
    assert resp.status_code == 302
    assert "/admin/login" in resp.headers["Location"]


def test_admin_can_verify_supplier(client, app):
    with app.app_context():
        supplier = Supplier.query.filter_by(name="Тестовый поставщик").first()
        supplier.verified = False
        db.session.commit()
        supplier_id = supplier.id

    _login_admin(client, app)
    resp = client.post(f"/admin/suppliers/{supplier_id}/verify", follow_redirects=True)
    assert resp.status_code == 200

    detail = client.get("/catalog/test-water")
    assert ">проверено<".encode() in detail.data


def test_admin_can_delete_supplier(client, app):
    with app.app_context():
        supplier = Supplier.query.filter_by(name="Тестовый поставщик").first()
        supplier_id = supplier.id

    _login_admin(client, app)
    resp = client.post(f"/admin/suppliers/{supplier_id}/delete", follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        assert db.session.get(Supplier, supplier_id) is None
