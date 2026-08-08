from app.models import EquipmentType, Material, Region, ServiceCategory, User

from tests.conftest import register


def test_customer_fills_own_profile(client):
    register(client, email="cust@example.com", role="customer")

    with client.application.app_context():
        region_id = Region.query.first().id

    resp = client.post(
        "/profile/customer",
        data={
            "kind": "company", "display_name": "ООО Ромашка", "phone": "+998901234567",
            "stir_inn": "123456789", "region_id": str(region_id), "city_id": "",
            "address_text": "г. Ташкент, ул. Промышленная, 1",
            "latitude": "41.31", "longitude": "69.28",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200

    with client.application.app_context():
        user = User.query.filter_by(email="cust@example.com").first()
        assert user.customer_profile.display_name == "ООО Ромашка"
        assert user.customer_profile.is_complete is True
        assert user.phone == "+998901234567"


def test_customer_profile_incomplete_without_required_fields(client):
    register(client, email="cust3@example.com", role="customer")
    with client.application.app_context():
        user = User.query.filter_by(email="cust3@example.com").first()
        assert user.customer_profile is None  # ещё не создан до первого сохранения


def test_executor_fills_profile_equipment_and_capabilities(client):
    register(client, email="exec@example.com", role="executor")

    with client.application.app_context():
        region_id = Region.query.first().id
        equipment_type_id = EquipmentType.query.first().id
        service_id = ServiceCategory.query.first().id
        material_id = Material.query.first().id

    client.post(
        "/profile/executor",
        data={
            "org_type": "tsekh", "display_name": "Цех Прогресс", "description": "Токарные и фрезерные работы",
            "phone": "+998901112233", "stir_inn": "", "region_id": str(region_id), "city_id": "",
            "address_text": "г. Ташкент, промзона", "latitude": "41.30", "longitude": "69.25",
            "service_radius_km": "80",
        },
        follow_redirects=True,
    )

    with client.application.app_context():
        user = User.query.filter_by(email="exec@example.com").first()
        assert user.executor_profile.display_name == "Цех Прогресс"
        assert user.executor_profile.is_complete is False  # ещё нет оборудования/техвозможностей

    client.post(
        "/profile/executor/equipment/add",
        data={"equipment_type_id": str(equipment_type_id), "model_name": "DMG MORI", "quantity": "2", "notes": ""},
        follow_redirects=True,
    )

    client.post(
        "/profile/executor/capabilities",
        data={
            "max_length_mm": "2000", "max_diameter_mm": "300", "max_width_mm": "", "max_height_mm": "",
            "max_weight_kg": "500", "service_category_ids": [str(service_id)], "material_ids": [str(material_id)],
        },
        follow_redirects=True,
    )

    with client.application.app_context():
        user = User.query.filter_by(email="exec@example.com").first()
        profile = user.executor_profile
        assert len(profile.equipment) == 1
        assert profile.capability.max_length_mm == 2000
        assert len(profile.capability.service_categories) == 1
        assert profile.is_complete is True


def test_executor_payment_methods_and_workload_saved_and_shown_on_public_profile(client):
    register(client, email="execpm@example.com", role="executor")
    with client.application.app_context():
        region_id = Region.query.first().id

    client.post(
        "/profile/executor",
        data={
            "org_type": "master", "display_name": "Мастер ПМ", "region_id": str(region_id),
            "address_text": "Ташкент", "payment_methods": ["cash", "payme"], "workload": "7",
        },
        follow_redirects=True,
    )

    with client.application.app_context():
        user = User.query.filter_by(email="execpm@example.com").first()
        profile = user.executor_profile
        assert profile.payment_methods == "cash,payme"
        assert profile.workload == 7
        user_id = user.id

    resp = client.get(f"/profile/executor/{user_id}")
    assert "Наличные".encode() in resp.data
    assert "Payme".encode() in resp.data
    assert "Загруженность: 7/10".encode() in resp.data


def test_executor_workload_out_of_range_is_ignored(client):
    register(client, email="execpm2@example.com", role="executor")
    with client.application.app_context():
        region_id = Region.query.first().id

    client.post(
        "/profile/executor",
        data={
            "org_type": "master", "display_name": "Мастер ПМ2", "region_id": str(region_id),
            "address_text": "Ташкент", "workload": "15",
        },
        follow_redirects=True,
    )
    with client.application.app_context():
        profile = User.query.filter_by(email="execpm2@example.com").first().executor_profile
        assert profile.workload is None


def test_constructor_payment_methods_and_workload_saved_and_shown(client):
    register(client, email="constrpm@example.com", role="constructor")
    with client.application.app_context():
        region_id = Region.query.first().id

    client.post(
        "/profile/constructor",
        data={
            "display_name": "КБ Точка", "description": "Чертежи на заказ", "region_id": str(region_id),
            "payment_methods": ["card", "click"], "workload": "3",
        },
        follow_redirects=True,
    )

    with client.application.app_context():
        user = User.query.filter_by(email="constrpm@example.com").first()
        profile = user.constructor_profile
        assert profile.payment_methods == "card,click"
        assert profile.workload == 3
        profile_id = profile.id

    resp = client.get(f"/constructors/{profile_id}")
    assert "Картой".encode() in resp.data
    assert "Click".encode() in resp.data
    assert "Загруженность: 3/10".encode() in resp.data


def test_executor_equipment_delete_is_scoped_to_owner(client):
    register(client, email="exec2@example.com", role="executor")
    with client.application.app_context():
        region_id = Region.query.first().id
        equipment_type_id = EquipmentType.query.first().id

    client.post(
        "/profile/executor",
        data={
            "org_type": "master", "display_name": "Мастер Иванов", "region_id": str(region_id),
            "address_text": "где-то", "latitude": "", "longitude": "", "service_radius_km": "30",
        },
        follow_redirects=True,
    )
    client.post(
        "/profile/executor/equipment/add",
        data={"equipment_type_id": str(equipment_type_id), "model_name": "", "quantity": "1", "notes": ""},
        follow_redirects=True,
    )

    with client.application.app_context():
        user = User.query.filter_by(email="exec2@example.com").first()
        item_id = user.executor_profile.equipment[0].id

    client.get("/auth/logout")
    register(client, email="other@example.com", role="executor")

    resp = client.post(f"/profile/executor/equipment/{item_id}/delete", follow_redirects=False)
    assert resp.status_code == 404
