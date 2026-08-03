from app import db
from app.models import EditSuggestion


def test_suggest_edit_creates_pending_suggestion(client, app):
    resp = client.post(
        "/sacred/test-source/suggest",
        data={
            "field_name": "belief",
            "proposed_value": "Новый текст верования",
            "message": "источник: личный опыт",
            "submitter_name": "Аноним",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "модерацию".encode() in resp.data

    with app.app_context():
        suggestion = EditSuggestion.query.first()
        assert suggestion is not None
        assert suggestion.field_name == "belief"
        assert suggestion.proposed_value == "Новый текст верования"
        assert suggestion.status == EditSuggestion.STATUS_PENDING


def test_suggest_edit_honeypot_blocks_silently(client, app):
    resp = client.post(
        "/sacred/test-source/suggest",
        data={
            "field_name": "belief",
            "proposed_value": "Спам",
            "website": "http://spam.example",  # заполненное honeypot-поле
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200

    with app.app_context():
        assert EditSuggestion.query.count() == 0


def test_admin_suggestions_requires_login(client):
    resp = client.get("/admin/suggestions")
    assert resp.status_code == 302
    assert "/admin/login" in resp.headers["Location"]


def test_admin_login_wrong_password(client):
    resp = client.post("/admin/login", data={"password": "wrong"}, follow_redirects=True)
    assert resp.status_code == 200
    assert "Неверный пароль".encode() in resp.data


def _login_admin(client, app):
    password = app.config["ADMIN_PASSWORD"]
    return client.post("/admin/login", data={"password": password}, follow_redirects=True)


def test_admin_approve_applies_change_to_source(client, app):
    client.post(
        "/sacred/test-source/suggest",
        data={"field_name": "comment", "proposed_value": "Одобренный комментарий"},
    )
    with app.app_context():
        suggestion = EditSuggestion.query.first()
        suggestion_id = suggestion.id

    _login_admin(client, app)
    resp = client.post(f"/admin/suggestions/{suggestion_id}/approve", follow_redirects=True)
    assert resp.status_code == 200

    detail = client.get("/sacred/test-source")
    assert "Одобренный комментарий".encode() in detail.data

    with app.app_context():
        suggestion = db.session.get(EditSuggestion, suggestion_id)
        assert suggestion.status == EditSuggestion.STATUS_APPROVED


def test_admin_reject_does_not_change_source(client, app):
    client.post(
        "/sacred/test-source/suggest",
        data={"field_name": "comment", "proposed_value": "Отклонённый комментарий"},
    )
    with app.app_context():
        suggestion = EditSuggestion.query.filter_by(proposed_value="Отклонённый комментарий").first()
        suggestion_id = suggestion.id

    _login_admin(client, app)
    resp = client.post(f"/admin/suggestions/{suggestion_id}/reject", follow_redirects=True)
    assert resp.status_code == 200

    detail = client.get("/sacred/test-source")
    assert "Отклонённый комментарий".encode() not in detail.data

    with app.app_context():
        suggestion = db.session.get(EditSuggestion, suggestion_id)
        assert suggestion.status == EditSuggestion.STATUS_REJECTED
