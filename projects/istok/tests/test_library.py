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


def test_library_detail(client):
    resp = client.get("/library/test-book")
    assert resp.status_code == 200
    assert "Тестовая книга".encode() in resp.data


def test_library_detail_404(client):
    resp = client.get("/library/does-not-exist")
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


def test_add_book_blocked_until_confirmed(client):
    client.post(
        "/auth/register",
        data={"email": "unconfirmedbook@user.example", "password": "password123", "password2": "password123"},
    )
    resp = client.post(
        "/library/add",
        data={"title": "Спам-книга", "author": "Автор", "description": "Описание."},
        follow_redirects=True,
    )
    assert "подтвердите email".encode() in resp.data

    from app.models import Book

    assert Book.query.filter_by(title="Спам-книга").first() is None


def test_add_book_after_confirmation(client, app):
    _register_and_confirm(client, app, "bookowner@user.example")

    resp = client.post(
        "/library/add",
        data={"title": "Новая тестовая книга", "author": "Тестовый автор", "description": "Описание книги."},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "не проверено".encode() in resp.data

    with app.app_context():
        from app.models import Book

        book = Book.query.filter_by(title="Новая тестовая книга").first()
        assert book is not None
        assert book.verified is False
        assert book.added_by_user_id is not None
