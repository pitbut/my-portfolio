from itsdangerous import URLSafeTimedSerializer

from app import db
from app.models import Book, User
from app.routes.auth import CONFIRM_SALT


def _login_admin(client, app):
    return client.post("/admin/login", data={"password": app.config["ADMIN_PASSWORD"]}, follow_redirects=True)


def _register_and_confirm(client, app, email):
    client.post(
        "/auth/register",
        data={"email": email, "password": "password123", "password2": "password123"},
    )
    with app.app_context():
        token = URLSafeTimedSerializer(app.config["SECRET_KEY"]).dumps(email, salt=CONFIRM_SALT)
    client.get(f"/auth/confirm/{token}")


def test_admin_users_requires_login(client):
    resp = client.get("/admin/users")
    assert resp.status_code == 302
    assert "/admin/login" in resp.headers["Location"]


def test_admin_users_list_shows_registered_users(client, app):
    _register_and_confirm(client, app, "listeduser@user.example")

    _login_admin(client, app)
    resp = client.get("/admin/users")
    assert resp.status_code == 200
    assert "listeduser@user.example".encode() in resp.data


def test_admin_user_detail_shows_additions(client, app):
    _register_and_confirm(client, app, "additionuser@user.example")
    client.post(
        "/library/add",
        data={"title": "Книга для теста админки", "author": "Автор", "description": "Описание."},
    )

    with app.app_context():
        user_id = User.query.filter_by(email="additionuser@user.example").first().id

    _login_admin(client, app)
    resp = client.get(f"/admin/users/{user_id}")
    assert resp.status_code == 200
    assert "Книга для теста админки".encode() in resp.data
    assert "не проверено".encode() in resp.data


def test_admin_can_edit_content(client, app):
    _register_and_confirm(client, app, "editcontent@user.example")
    client.post(
        "/library/add",
        data={"title": "Книга до правки", "author": "Автор", "description": "Описание."},
    )

    with app.app_context():
        book_id = Book.query.filter_by(title="Книга до правки").first().id

    _login_admin(client, app)
    resp = client.post(
        f"/admin/content/book/{book_id}/edit",
        data={"title": "Книга после правки", "author": "Автор", "year": "", "genre": "", "description": "Новое описание."},
        follow_redirects=True,
    )
    assert resp.status_code == 200

    with app.app_context():
        book = db.session.get(Book, book_id)
        assert book.title == "Книга после правки"
        assert book.description == "Новое описание."


def test_admin_can_delete_content_by_type(client, app):
    _register_and_confirm(client, app, "deletecontent@user.example")
    client.post(
        "/library/add",
        data={"title": "Книга на удаление", "author": "Автор", "description": "Описание."},
    )

    with app.app_context():
        book_id = Book.query.filter_by(title="Книга на удаление").first().id

    _login_admin(client, app)
    resp = client.post(f"/admin/content/book/{book_id}/delete", follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        assert db.session.get(Book, book_id) is None


def test_admin_delete_user_keeps_their_additions(client, app):
    _register_and_confirm(client, app, "deleteuser@user.example")
    client.post(
        "/library/add",
        data={"title": "Книга остаётся после удаления автора", "author": "Автор", "description": "Описание."},
    )

    with app.app_context():
        user_id = User.query.filter_by(email="deleteuser@user.example").first().id
        book_id = Book.query.filter_by(title="Книга остаётся после удаления автора").first().id

    _login_admin(client, app)
    resp = client.post(f"/admin/users/{user_id}/delete", follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        assert db.session.get(User, user_id) is None
        book = db.session.get(Book, book_id)
        assert book is not None
        assert book.added_by_user_id is None
