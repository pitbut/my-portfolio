def test_index_page(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Исток".encode() in resp.data


def test_equipment_page(client):
    resp = client.get("/equipment")
    assert resp.status_code == 200
    assert "Тестовый фильтр".encode() in resp.data


def test_experiments_page(client):
    resp = client.get("/experiments")
    assert resp.status_code == 200
    assert "Тестовый опыт".encode() in resp.data


def test_delivery_page(client):
    resp = client.get("/delivery")
    assert resp.status_code == 200
    assert "Тестовая доставка".encode() in resp.data


def test_equipment_search(client):
    resp = client.get("/equipment?q=фильтр")
    assert resp.status_code == 200
    assert "Тестовый фильтр".encode() in resp.data

    resp = client.get("/equipment?q=несуществующий-запрос-xyz")
    assert "Тестовый фильтр".encode() not in resp.data


def test_equipment_category_filter(client):
    resp = client.get("/equipment?category=Фильтр")
    assert "Тестовый фильтр".encode() in resp.data

    resp = client.get("/equipment?category=Кулер")
    assert "Тестовый фильтр".encode() not in resp.data


def test_equipment_detail_page(client):
    resp = client.get("/equipment/test-filter")
    assert resp.status_code == 200
    assert "Тестовый фильтр".encode() in resp.data
    assert "проверено".encode() in resp.data


def test_equipment_detail_404(client):
    resp = client.get("/equipment/does-not-exist")
    assert resp.status_code == 404


def test_equipment_add_requires_login(client):
    resp = client.get("/equipment/add")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


def test_experiment_detail_page(client):
    resp = client.get("/experiments/test-experiment")
    assert resp.status_code == 200
    assert "Тестовый опыт".encode() in resp.data


def test_delivery_detail_page(client):
    resp = client.get("/delivery/test-delivery")
    assert resp.status_code == 200
    assert "Тестовая доставка".encode() in resp.data


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


def test_add_experiment_blocked_until_confirmed(client):
    client.post(
        "/auth/register",
        data={"email": "unconfirmedexp@user.example", "password": "password123", "password2": "password123"},
    )
    resp = client.post(
        "/experiments/add",
        data={"title": "Спам-опыт", "description": "Описание.", "verdict": "миф"},
        follow_redirects=True,
    )
    assert "подтвердите email".encode() in resp.data

    from app.models import Experiment

    assert Experiment.query.filter_by(title="Спам-опыт").first() is None


def test_add_experiment_after_confirmation(client, app):
    _register_and_confirm(client, app, "expowner@user.example")

    resp = client.post(
        "/experiments/add",
        data={"title": "Новый тестовый опыт", "description": "Описание опыта.", "verdict": "наука"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "не проверено".encode() in resp.data

    with app.app_context():
        from app.models import Experiment

        experiment = Experiment.query.filter_by(title="Новый тестовый опыт").first()
        assert experiment is not None
        assert experiment.verified is False
        assert experiment.added_by_user_id is not None


def test_add_delivery_blocked_until_confirmed(client):
    client.post(
        "/auth/register",
        data={"email": "unconfirmeddel@user.example", "password": "password123", "password2": "password123"},
    )
    resp = client.post(
        "/delivery/add",
        data={"name": "Спам-доставка", "delivery_time": "1 день"},
        follow_redirects=True,
    )
    assert "подтвердите email".encode() in resp.data

    from app.models import DeliveryService

    assert DeliveryService.query.filter_by(name="Спам-доставка").first() is None


def test_add_delivery_after_confirmation(client, app):
    _register_and_confirm(client, app, "delowner@user.example")

    resp = client.post(
        "/delivery/add",
        data={"name": "Новая тестовая доставка", "delivery_time": "2 дня", "price_rub": "200"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "не проверено".encode() in resp.data

    with app.app_context():
        from app.models import DeliveryService

        service = DeliveryService.query.filter_by(name="Новая тестовая доставка").first()
        assert service is not None
        assert service.verified is False
        assert service.added_by_user_id is not None
