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
