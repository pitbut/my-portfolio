def _login_admin(client, app):
    return client.post("/admin/login", data={"password": app.config["ADMIN_PASSWORD"]}, follow_redirects=True)


def test_visit_counter_increments_on_page_view(client, app):
    from app.models import SiteStat

    with app.app_context():
        before = SiteStat.query.get(1)
        before_count = before.total_views if before else 0

    client.get("/")
    client.get("/catalog/")

    with app.app_context():
        after = SiteStat.query.get(1)
        assert after.total_views >= before_count + 2


def test_visit_counter_ignores_admin_and_static(client, app):
    from app.models import SiteStat

    with app.app_context():
        before = SiteStat.query.get(1)
        before_count = before.total_views if before else 0

    client.get("/admin/login")

    with app.app_context():
        after = SiteStat.query.get(1)
        after_count = after.total_views if after else 0
        assert after_count == before_count


def test_admin_sees_visit_counter(client, app):
    client.get("/")
    _login_admin(client, app)
    resp = client.get("/admin/users")
    assert "просмотров сайта".encode() in resp.data
