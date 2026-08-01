def test_sacred_index(client):
    resp = client.get("/sacred/")
    assert resp.status_code == 200
    assert "Тестовый источник".encode() in resp.data


def test_sacred_detail(client):
    resp = client.get("/sacred/test-source")
    assert resp.status_code == 200
    assert "Люди верят, что вода исполняет желания.".encode() in resp.data


def test_sacred_detail_404(client):
    resp = client.get("/sacred/does-not-exist")
    assert resp.status_code == 404
