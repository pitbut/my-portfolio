def test_sacred_index(client):
    resp = client.get("/sacred/")
    assert resp.status_code == 200
    assert "Тестовый источник".encode() in resp.data


def test_sacred_detail(client):
    resp = client.get("/sacred/test-source")
    assert resp.status_code == 200
    assert "Люди верят, что вода исполняет желания.".encode() in resp.data


def test_sacred_detail_shows_comment_and_image(client):
    resp = client.get("/sacred/test-source")
    assert resp.status_code == 200
    assert "Тестовый комментарий редакции.".encode() in resp.data
    assert b"/static/img/sacred/test-source.jpg" in resp.data


def test_sacred_detail_404(client):
    resp = client.get("/sacred/does-not-exist")
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


def test_add_source_blocked_until_confirmed(client):
    client.post(
        "/auth/register",
        data={"email": "unconfirmedsrc@user.example", "password": "password123", "password2": "password123"},
    )
    resp = client.post(
        "/sacred/add",
        data={
            "name": "Спам-источник", "country": "Тестландия", "location": "где-то",
            "belief": "верят", "allowed": "можно", "forbidden": "нельзя",
        },
        follow_redirects=True,
    )
    assert "подтвердите email".encode() in resp.data

    from app.models import SacredSource

    assert SacredSource.query.filter_by(name="Спам-источник").first() is None


def test_add_source_after_confirmation(client, app):
    _register_and_confirm(client, app, "srcowner@user.example")

    resp = client.post(
        "/sacred/add",
        data={
            "name": "Новый тестовый источник", "country": "Тестландия", "location": "где-то у моря",
            "belief": "верят в чудо", "allowed": "фотографировать", "forbidden": "мусорить",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "не проверено".encode() in resp.data

    with app.app_context():
        from app.models import SacredSource

        source = SacredSource.query.filter_by(name="Новый тестовый источник").first()
        assert source is not None
        assert source.verified is False
        assert source.added_by_user_id is not None
