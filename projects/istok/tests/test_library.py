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


def test_add_book_with_files_and_download(client, app):
    from io import BytesIO

    _register_and_confirm(client, app, "bookfiles@user.example")

    resp = client.post(
        "/library/add",
        data={
            "title": "Книга с файлами",
            "author": "Автор",
            "description": "Описание.",
            "book_files": [
                (BytesIO(b"%PDF-1.4 fake pdf"), "book.pdf"),
                (BytesIO(b"fake epub"), "book.epub"),
            ],
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "PDF".encode() in resp.data
    assert "EPUB".encode() in resp.data

    with app.app_context():
        from app.models import Book

        book = Book.query.filter_by(title="Книга с файлами").first()
        assert len(book.files) == 2
        formats = {f.format for f in book.files}
        assert formats == {"pdf", "epub"}
        file_id = book.files[0].id
        slug = book.slug

    download_resp = client.get(f"/library/{slug}/download/{file_id}")
    assert download_resp.status_code == 200
    assert download_resp.headers["Content-Disposition"].startswith("attachment")


def _login_admin(client, app):
    password = app.config["ADMIN_PASSWORD"]
    return client.post("/admin/login", data={"password": password}, follow_redirects=True)


def test_admin_can_add_and_remove_book_file(client, app):
    from io import BytesIO

    _register_and_confirm(client, app, "bookmanage@user.example")
    client.post(
        "/library/add",
        data={"title": "Книга для управления", "author": "Автор", "description": "Описание."},
        follow_redirects=True,
    )
    with app.app_context():
        from app.models import Book

        book_id = Book.query.filter_by(title="Книга для управления").first().id

    client.get("/auth/logout")
    _login_admin(client, app)

    resp = client.post(
        f"/admin/content/book/{book_id}/files/add",
        data={"book_files": [(BytesIO(b"fake fb2 content"), "book.fb2")]},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "FB2".encode() in resp.data

    with app.app_context():
        from app.models import Book

        book = Book.query.get(book_id)
        assert len(book.files) == 1
        file_id = book.files[0].id

    resp = client.post(
        f"/admin/content/book/{book_id}/files/{file_id}/delete",
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "Файл удалён".encode() in resp.data

    with app.app_context():
        from app.models import Book

        book = Book.query.get(book_id)
        assert len(book.files) == 0


def test_add_book_rejects_unsupported_file_format(client, app):
    from io import BytesIO

    _register_and_confirm(client, app, "bookbadfile@user.example")

    resp = client.post(
        "/library/add",
        data={
            "title": "Книга с плохим файлом",
            "author": "Автор",
            "description": "Описание.",
            "book_files": [(BytesIO(b"malicious"), "virus.exe")],
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "не поддерживается".encode() in resp.data

    with app.app_context():
        from app.models import Book

        book = Book.query.filter_by(title="Книга с плохим файлом").first()
        assert book is not None
        assert len(book.files) == 0
