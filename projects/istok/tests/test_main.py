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
