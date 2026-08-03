def test_catalog_detail_page(client):
    resp = client.get("/catalog/test-water")
    assert resp.status_code == 200
    assert "Тестовая вода".encode() in resp.data
    assert "Тестовый поставщик".encode() in resp.data
    assert "проверено".encode() in resp.data


def test_catalog_detail_404(client):
    resp = client.get("/catalog/does-not-exist")
    assert resp.status_code == 404


def test_add_supplier_requires_login(client):
    resp = client.get("/catalog/test-water/add-supplier")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]
