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


def test_add_article_blocked_until_confirmed(client):
    client.post(
        "/auth/register",
        data={"email": "unconfirmedart@user.example", "password": "password123", "password2": "password123"},
    )
    resp = client.post(
        "/articles/add",
        data={"title": "Спам-статья", "category": "Прочее", "body": "Текст."},
        follow_redirects=True,
    )
    assert "подтвердите email".encode() in resp.data

    from app.models import Article

    assert Article.query.filter_by(title="Спам-статья").first() is None


def test_add_article_after_confirmation(client, app):
    _register_and_confirm(client, app, "artowner@user.example")

    resp = client.post(
        "/articles/add",
        data={"title": "Новая тестовая статья", "category": "Наука", "body": "Текст новой статьи."},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "не проверено".encode() in resp.data

    with app.app_context():
        from app.models import Article

        article = Article.query.filter_by(title="Новая тестовая статья").first()
        assert article is not None
        assert article.verified is False
        assert article.added_by_user_id is not None
