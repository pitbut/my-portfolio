def test_library_index(client):
    resp = client.get("/library/")
    assert resp.status_code == 200
    assert "Тестовая книга".encode() in resp.data


def test_library_filter_by_genre(client):
    resp = client.get("/library/?genre=наука")
    assert resp.status_code == 200
    assert "Тестовая книга".encode() in resp.data

    resp_empty = client.get("/library/?genre=несуществующий-жанр")
    assert resp_empty.status_code == 200
    assert "Тестовая книга".encode() not in resp_empty.data
