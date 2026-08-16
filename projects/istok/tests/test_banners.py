def _login_admin(client, app):
    return client.post("/admin/login", data={"password": app.config["ADMIN_PASSWORD"]}, follow_redirects=True)


def test_homepage_without_banners(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "banner-row".encode() not in resp.data


def test_admin_banners_requires_login(client):
    resp = client.get("/admin/banners")
    assert resp.status_code == 302
    assert "/admin/login" in resp.headers["Location"]


def test_admin_can_set_text_banner(client, app):
    _login_admin(client, app)
    resp = client.post(
        "/admin/banners/1/edit",
        data={"banner_type": "text", "title": "Скидка на воду", "text_content": "Только сегодня -20%!"},
        follow_redirects=True,
    )
    assert resp.status_code == 200

    with app.app_context():
        from app.models import Banner

        banner = Banner.query.filter_by(slot=1).first()
        assert banner is not None
        assert banner.banner_type == "text"
        assert banner.text_content == "Только сегодня -20%!"

    home = client.get("/")
    assert "Скидка на воду".encode() in home.data
    assert "Только сегодня -20%!".encode() in home.data


def test_admin_can_clear_banner(client, app):
    _login_admin(client, app)
    client.post(
        "/admin/banners/2/edit",
        data={"banner_type": "text", "text_content": "Временный баннер"},
    )
    resp = client.post("/admin/banners/2/clear", follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        from app.models import Banner

        assert Banner.query.filter_by(slot=2).first() is None
