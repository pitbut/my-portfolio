from app.models import ContactMessage


def test_contact_page(client):
    resp = client.get("/contact")
    assert resp.status_code == 200


def test_contact_form_submission(client, app):
    resp = client.post(
        "/contact",
        data={"name": "Аноним", "email": "anon@example.com", "message": "Проверка формы"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "отправлено".encode() in resp.data

    with app.app_context():
        msg = ContactMessage.query.filter_by(message="Проверка формы").first()
        assert msg is not None
        assert msg.email == "anon@example.com"


def test_contact_form_requires_message(client):
    resp = client.post("/contact", data={"message": ""}, follow_redirects=True)
    assert "Напишите текст сообщения".encode() in resp.data


def test_contact_form_honeypot(client, app):
    client.post(
        "/contact",
        data={"message": "Спам", "website": "http://spam.example"},
    )
    with app.app_context():
        assert ContactMessage.query.filter_by(message="Спам").first() is None
