def test_catalog_index(client):
    resp = client.get("/catalog/")
    assert resp.status_code == 200
    assert "Тестовая вода".encode() in resp.data


def test_catalog_sorting(client):
    resp = client.get("/catalog/?sort=price_desc")
    assert resp.status_code == 200

    resp_invalid = client.get("/catalog/?sort=not-a-real-option")
    assert resp_invalid.status_code == 200
