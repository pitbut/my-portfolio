from werkzeug.security import generate_password_hash

from app import db
from app.models import ConstructorProfile, ExecutorProfile, Region, User

from tests.conftest import register
from tests.test_orders import _login, _setup_executor


def test_switch_role_updates_current_user_and_redirects(client):
    register(client, email="switcher@example.com", role="customer")
    resp = client.post("/settings/switch-role", data={"role": "executor"}, follow_redirects=True)
    assert resp.status_code == 200
    assert "Профиль исполнителя".encode() in resp.data

    with client.application.app_context():
        user = User.query.filter_by(email="switcher@example.com").first()
        assert user.role == "executor"


def test_cannot_switch_to_admin_or_same_role(client):
    register(client, email="switcher2@example.com", role="customer")

    resp = client.post("/settings/switch-role", data={"role": "admin"}, follow_redirects=True)
    assert "Недопустимая смена роли".encode() in resp.data
    with client.application.app_context():
        assert User.query.filter_by(email="switcher2@example.com").first().role == "customer"

    resp = client.post("/settings/switch-role", data={"role": "customer"}, follow_redirects=True)
    assert "Недопустимая смена роли".encode() in resp.data


def test_admin_cannot_use_switch_role(client):
    admin = User(email="admin@example.com", password_hash=generate_password_hash("password123"), role="admin", email_confirmed=True)
    db.session.add(admin)
    db.session.commit()
    _login(client, "admin@example.com")

    resp = client.post("/settings/switch-role", data={"role": "executor"}, follow_redirects=True)
    assert "Недопустимая смена роли".encode() in resp.data
    with client.application.app_context():
        assert User.query.filter_by(email="admin@example.com").first().role == "admin"


def test_switching_away_from_executor_hides_from_map_but_keeps_data(client):
    with client.application.app_context():
        region_id = Region.query.first().id
    _setup_executor(client, "flipflop@example.com", region_id)

    _login(client, "flipflop@example.com")
    resp = client.get("/map/executors.json")
    assert len(resp.get_json()) == 1

    client.post("/settings/switch-role", data={"role": "customer"}, follow_redirects=True)
    resp = client.get("/map/executors.json")
    assert resp.get_json() == []

    with client.application.app_context():
        profile = ExecutorProfile.query.join(ExecutorProfile.user).filter_by(email="flipflop@example.com").first()
        assert profile is not None
        assert profile.display_name  # старые данные никуда не делись

    client.post("/settings/switch-role", data={"role": "executor"}, follow_redirects=True)
    resp = client.get("/map/executors.json")
    assert len(resp.get_json()) == 1


def test_switching_away_from_constructor_hides_from_catalog_but_keeps_data(client):
    register(client, email="flipdesigner@example.com", role="constructor")
    with client.application.app_context():
        region_id = Region.query.first().id
    client.post(
        "/profile/constructor",
        data={"display_name": "Дизайнер на переключении", "description": "Черчу", "region_id": str(region_id)},
        follow_redirects=True,
    )

    resp = client.get("/constructors")
    assert "Дизайнер на переключении".encode() in resp.data

    client.post("/settings/switch-role", data={"role": "customer"}, follow_redirects=True)
    resp = client.get("/constructors")
    assert "Дизайнер на переключении".encode() not in resp.data

    with client.application.app_context():
        profile = ConstructorProfile.query.join(ConstructorProfile.user).filter_by(email="flipdesigner@example.com").first()
        assert profile is not None
        assert profile.display_name == "Дизайнер на переключении"

    client.post("/settings/switch-role", data={"role": "constructor"}, follow_redirects=True)
    resp = client.get("/constructors")
    assert "Дизайнер на переключении".encode() in resp.data
