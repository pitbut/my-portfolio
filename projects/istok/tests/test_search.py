def test_search_empty_query(client):
    resp = client.get("/search")
    assert resp.status_code == 200
    assert "Введите запрос".encode() in resp.data


def test_search_no_results(client):
    resp = client.get("/search?q=несуществующийзапросxyz123")
    assert resp.status_code == 200
    assert "ничего не нашлось".encode() in resp.data


def test_search_finds_water_brand(client):
    resp = client.get("/search?q=Тестовая вода")
    assert resp.status_code == 200
    assert "Тестовая вода".encode() in resp.data
    assert "Марки воды".encode() in resp.data


def test_search_finds_across_multiple_sections(client):
    resp = client.get("/search?q=Тестов")
    assert resp.status_code == 200
    # "Тестов" встречается и в книге ("Автор Тестов"), и в источнике ("Тестовый источник")
    assert "Библиотека".encode() in resp.data
    assert "Священные источники".encode() in resp.data
