from app import db
from app.models import User
from tests.conftest import login


def _register(client, **overrides):
    data = {
        "name": "Гость",
        "email": "guest@example.com",
        "password": "password123",
        "password2": "password123",
        "age_confirm": "on",
    }
    data.update(overrides)
    return client.post("/auth/register", data=data, follow_redirects=True)


def test_register_creates_user_and_sends_to_confirm_pending(app, client):
    response = _register(client)
    assert response.status_code == 200
    with app.app_context():
        user = User.query.filter_by(email="guest@example.com").first()
        assert user is not None
        assert user.email_confirmed is False


def test_register_requires_age_confirmation(app, client):
    _register(client, age_confirm="")
    with app.app_context():
        assert User.query.filter_by(email="guest@example.com").first() is None


def test_register_rejects_short_password(app, client):
    _register(client, password="short", password2="short")
    with app.app_context():
        assert User.query.filter_by(email="guest@example.com").first() is None


def test_register_rejects_duplicate_email(app, client, user):
    _register(client, email="user@example.com")
    with app.app_context():
        assert User.query.filter_by(email="user@example.com").count() == 1


def test_login_requires_correct_password(client, user):
    response = login(client, password="wrong-password")
    assert response.status_code == 200
    assert "Неверный email или пароль" in response.get_data(as_text=True)


def test_login_success_reaches_dashboard(client, user):
    response = login(client)
    assert response.status_code == 200
    assert response.request.path == "/dashboard"


def test_unconfirmed_email_gates_access(app, client):
    _register(client)
    with app.app_context():
        u = User.query.filter_by(email="guest@example.com").first()
        assert u.email_confirmed is False

    response = client.get("/dashboard", follow_redirects=True)
    assert response.status_code == 200
    assert response.request.path == "/auth/confirm-pending"
    assert "Проверьте почту" in response.get_data(as_text=True)


def test_confirm_email_with_valid_token_grants_access(app, client):
    _register(client)
    with app.app_context():
        from app.routes.auth import confirm_url_for

        u = User.query.filter_by(email="guest@example.com").first()
        with app.test_request_context():
            confirm_url = confirm_url_for(u)

    response = client.get(confirm_url, follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        assert User.query.filter_by(email="guest@example.com").first().email_confirmed is True


def test_blocked_user_cannot_login(app, client, user):
    with app.app_context():
        u = db.session.get(User, user)
        u.is_blocked = True
        db.session.commit()

    response = login(client)
    assert response.status_code == 200
    assert response.request.path == "/auth/login"
    assert "заблокирован" in response.get_data(as_text=True)
