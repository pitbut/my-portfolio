def test_articles_index(client):
    resp = client.get("/articles/")
    assert resp.status_code == 200
    assert "Тестовая статья".encode() in resp.data


def test_article_detail(client):
    resp = client.get("/articles/test-article")
    assert resp.status_code == 200
    assert "Первый абзац.".encode() in resp.data


def test_article_detail_404(client):
    resp = client.get("/articles/does-not-exist")
    assert resp.status_code == 404
