def test_default_language_is_russian(client):
    resp = client.get("/")
    assert "Священные источники мира".encode() in resp.data


def test_switch_to_uzbek(client):
    client.get("/lang/uz")
    resp = client.get("/")
    assert "Dunyoning muqaddas manbalari".encode() in resp.data


def test_switch_to_english(client):
    client.get("/lang/en")
    resp = client.get("/")
    assert "Sacred sources of the world".encode() in resp.data


def test_language_persists_across_requests(client):
    client.get("/lang/en")
    resp = client.get("/catalog/")
    assert "Drinking water price catalog".encode() in resp.data


def test_invalid_language_code_ignored(client):
    resp = client.get("/lang/fr", follow_redirects=True)
    assert resp.status_code == 200
    assert "Священные источники мира".encode() in resp.data
