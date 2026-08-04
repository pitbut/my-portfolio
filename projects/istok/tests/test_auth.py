from itsdangerous import URLSafeTimedSerializer

from app.models import User
from app.routes.auth import CONFIRM_SALT


def _confirm_token(app, email):
    with app.app_context():
        serializer = URLSafeTimedSerializer(app.config["SECRET_KEY"])
        return serializer.dumps(email, salt=CONFIRM_SALT)


def test_register_creates_unconfirmed_user(client, app):
    resp = client.post(
        "/auth/register",
        data={"email": "new@user.example", "password": "password123", "password2": "password123"},
        follow_redirects=True,
    )
    assert resp.status_code == 200

    with app.app_context():
        user = User.query.filter_by(email="new@user.example").first()
        assert user is not None
        assert user.email_confirmed is False


def test_register_password_mismatch(client):
    resp = client.post(
        "/auth/register",
        data={"email": "mismatch@user.example", "password": "password123", "password2": "other12345"},
        follow_redirects=True,
    )
    assert "Пароли не совпадают".encode() in resp.data


def test_register_duplicate_email(client):
    client.post(
        "/auth/register",
        data={"email": "dup@user.example", "password": "password123", "password2": "password123"},
    )
    client.get("/auth/logout")
    resp = client.post(
        "/auth/register",
        data={"email": "dup@user.example", "password": "password123", "password2": "password123"},
        follow_redirects=True,
    )
    assert "уже зарегистрирован".encode() in resp.data


def test_confirm_email_with_valid_token(client, app):
    client.post(
        "/auth/register",
        data={"email": "confirm@user.example", "password": "password123", "password2": "password123"},
    )
    token = _confirm_token(app, "confirm@user.example")
    resp = client.get(f"/auth/confirm/{token}", follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        user = User.query.filter_by(email="confirm@user.example").first()
        assert user.email_confirmed is True


def test_confirm_email_invalid_token(client):
    resp = client.get("/auth/confirm/not-a-real-token", follow_redirects=True)
    assert "недействительна".encode() in resp.data


def test_login_wrong_password(client):
    client.post(
        "/auth/register",
        data={"email": "login@user.example", "password": "password123", "password2": "password123"},
    )
    client.get("/auth/logout")
    resp = client.post(
        "/auth/login",
        data={"email": "login@user.example", "password": "wrong"},
        follow_redirects=True,
    )
    assert "Неверный email или пароль".encode() in resp.data


def test_login_and_logout(client):
    client.post(
        "/auth/register",
        data={"email": "loginok@user.example", "password": "password123", "password2": "password123"},
    )
    client.get("/auth/logout")
    resp = client.post(
        "/auth/login",
        data={"email": "loginok@user.example", "password": "password123"},
        follow_redirects=True,
    )
    assert "loginok@user.example".encode() in resp.data

    resp = client.get("/auth/logout", follow_redirects=True)
    assert "loginok@user.example".encode() not in resp.data


def test_add_supplier_blocked_until_confirmed(client, app):
    client.post(
        "/auth/register",
        data={"email": "unconfirmed@user.example", "password": "password123", "password2": "password123"},
    )
    resp = client.post(
        "/catalog/test-water/add-supplier",
        data={"name": "Спам склад", "address": "где-то"},
        follow_redirects=True,
    )
    assert "подтвердите email".encode() in resp.data

    with app.app_context():
        from app.models import Supplier

        assert Supplier.query.filter_by(name="Спам склад").first() is None


def test_add_supplier_after_confirmation(client, app):
    client.post(
        "/auth/register",
        data={"email": "confirmedadd@user.example", "password": "password123", "password2": "password123"},
    )
    token = _confirm_token(app, "confirmedadd@user.example")
    client.get(f"/auth/confirm/{token}")

    resp = client.post(
        "/catalog/test-water/add-supplier",
        data={"name": "Новый склад", "address": "Складская ул., 5", "supplier_type": "опт"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "не проверено".encode() in resp.data

    with app.app_context():
        from app.models import Supplier

        supplier = Supplier.query.filter_by(name="Новый склад").first()
        assert supplier is not None
        assert supplier.verified is False
        assert supplier.added_by_user_id is not None


def test_add_equipment_blocked_until_confirmed(client, app):
    client.post(
        "/auth/register",
        data={"email": "unconfirmedeq@user.example", "password": "password123", "password2": "password123"},
    )
    resp = client.post(
        "/equipment/add",
        data={"name": "Спам-фильтр", "category": "Фильтр", "description": "Спам."},
        follow_redirects=True,
    )
    assert "подтвердите email".encode() in resp.data

    with app.app_context():
        from app.models import Equipment

        assert Equipment.query.filter_by(name="Спам-фильтр").first() is None


def test_add_equipment_after_confirmation(client, app):
    client.post(
        "/auth/register",
        data={"email": "confirmedeq@user.example", "password": "password123", "password2": "password123"},
    )
    token = _confirm_token(app, "confirmedeq@user.example")
    client.get(f"/auth/confirm/{token}")

    resp = client.post(
        "/equipment/add",
        data={
            "name": "Новый фильтр",
            "category": "Фильтр",
            "description": "Описание нового фильтра.",
            "manufacturer": "Акварус",
            "price_rub": "2500",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "не проверено".encode() in resp.data

    with app.app_context():
        from app.models import Equipment

        item = Equipment.query.filter_by(name="Новый фильтр").first()
        assert item is not None
        assert item.verified is False
        assert item.added_by_user_id is not None
        assert item.slug


def test_pending_confirm_link_shown_when_mail_not_configured(client):
    client.post(
        "/auth/register",
        data={"email": "nomail@user.example", "password": "password123", "password2": "password123"},
        follow_redirects=True,
    )
    resp = client.get("/")
    assert "/auth/confirm/".encode() in resp.data


def test_pending_confirm_link_hidden_after_confirmation(client, app):
    client.post(
        "/auth/register",
        data={"email": "willconfirm@user.example", "password": "password123", "password2": "password123"},
        follow_redirects=True,  # consumes the one-time registration flash
    )
    token = _confirm_token(app, "willconfirm@user.example")
    client.get(f"/auth/confirm/{token}", follow_redirects=True)  # consumes the confirmation flash

    resp = client.get("/")
    assert "/auth/confirm/".encode() not in resp.data
