from app.models import ConstructorProfile, User

from tests.conftest import register


def _login(client, email, password="password123"):
    client.post("/auth/login", data={"email": email, "password": password}, follow_redirects=True)


def test_constructors_catalog_requires_auth(client):
    resp = client.get("/constructors", follow_redirects=False)
    assert resp.status_code == 302
    assert "auth_required=1" in resp.headers["Location"]


def test_register_as_constructor_and_fill_profile_shows_in_catalog(client):
    register(client, email="designer@example.com", role="constructor")
    with client.application.app_context():
        from app.models import Region

        region_id = Region.query.first().id

    resp = client.post(
        "/profile/constructor",
        data={
            "display_name": "Иван, конструктор-фрилансер", "description": "Черчу в КОМПАС, опыт 5 лет",
            "experience_years": "5", "region_id": str(region_id),
        },
        follow_redirects=True,
    )
    assert "видны в каталоге".encode() in resp.data

    resp = client.get("/constructors")
    assert "Иван, конструктор-фрилансер".encode() in resp.data


def test_incomplete_constructor_profile_hidden_from_catalog(client):
    register(client, email="incomplete_designer@example.com", role="constructor")
    client.get("/auth/logout")

    register(client, email="someone_else@example.com", role="customer")
    resp = client.get("/constructors")
    assert "incomplete_designer".encode() not in resp.data

    with client.application.app_context():
        profile = ConstructorProfile.query.filter_by(user_id=User.query.filter_by(email="incomplete_designer@example.com").first().id).first()
        assert profile is None  # анкета не сохранялась, пока не отправили форму


def test_customer_and_executor_can_both_message_constructor(client):
    register(client, email="designer2@example.com", role="constructor")
    with client.application.app_context():
        from app.models import Region

        region_id = Region.query.first().id
    client.post(
        "/profile/constructor",
        data={"display_name": "Студия чертежей", "description": "Проектирование металлоконструкций", "region_id": str(region_id)},
        follow_redirects=True,
    )
    with client.application.app_context():
        constructor_profile_id = ConstructorProfile.query.first().id
        constructor_user_id = ConstructorProfile.query.first().user_id
    client.get("/auth/logout")

    register(client, email="customer_seeking@example.com", role="customer")
    resp = client.get(f"/constructors/{constructor_profile_id}")
    assert resp.status_code == 200
    assert f'/messages/u/{constructor_user_id}'.encode() in resp.data
    client.get("/auth/logout")

    register(client, email="executor_seeking@example.com", role="executor")
    resp = client.get(f"/constructors/{constructor_profile_id}")
    assert resp.status_code == 200
    assert f'/messages/u/{constructor_user_id}'.encode() in resp.data


def test_constructor_role_gated_to_own_profile_route(client):
    register(client, email="customer_only@example.com", role="customer")
    resp = client.get("/profile/constructor", follow_redirects=False)
    assert resp.status_code == 403
