import io

from app import db
from app.models import Message, User, get_settings
from tests.conftest import login


class FakeProvider:
    def send_message(self, system_prompt, history, user_content, max_tokens=800):
        return "Тестовый ответ собеседника", {"input_tokens": 10, "output_tokens": 5}

    def build_image_content(self, text, image_bytes, mime_type):
        return [{"type": "text", "text": text}]


def _patch_provider(monkeypatch):
    monkeypatch.setattr("app.routes.chat.get_provider", lambda: FakeProvider())


def test_room_requires_companion_selected(app, client):
    with app.app_context():
        from werkzeug.security import generate_password_hash

        u = User(name="Без выбора", email="nocomp@example.com",
                 password_hash=generate_password_hash("password123"), email_confirmed=True)
        db.session.add(u)
        db.session.commit()

    login(client, email="nocomp@example.com")
    response = client.get("/room/", follow_redirects=True)
    assert response.status_code == 200
    assert response.request.path == "/dashboard"


def test_send_message_creates_history_and_increments_usage(app, client, user, monkeypatch):
    _patch_provider(monkeypatch)
    login(client)

    response = client.post("/room/message", json={"text": "Привет!"})
    assert response.status_code == 200
    data = response.get_json()
    assert data["reply"] == "Тестовый ответ собеседника"
    assert data["messages_used"] == 1

    with app.app_context():
        u = db.session.get(User, user)
        assert u.messages_used == 1
        assert Message.query.count() == 2


def test_action_request_uses_preset_prompt(app, client, user, monkeypatch):
    _patch_provider(monkeypatch)
    login(client)

    response = client.post("/room/message", json={"action": "toast"})
    assert response.status_code == 200
    assert response.get_json()["reply"] == "Тестовый ответ собеседника"


def test_limit_reached_blocks_further_messages(app, client, user, monkeypatch):
    _patch_provider(monkeypatch)
    with app.app_context():
        u = db.session.get(User, user)
        u.message_limit = 1
        db.session.commit()

    login(client)
    first = client.post("/room/message", json={"text": "Раз"})
    assert first.status_code == 200
    assert "limit_reached" not in first.get_json()

    second = client.post("/room/message", json={"text": "Два"})
    assert second.status_code == 200
    assert second.get_json().get("limit_reached") is True

    with app.app_context():
        assert Message.query.count() == 2  # второе сообщение не дошло до ИИ и не сохранилось


def test_disabling_limits_globally_allows_more_messages(app, client, user, monkeypatch):
    _patch_provider(monkeypatch)
    with app.app_context():
        u = db.session.get(User, user)
        u.message_limit = 1
        settings = get_settings()
        settings.limits_enabled = False
        db.session.commit()

    login(client)
    client.post("/room/message", json={"text": "Раз"})
    second = client.post("/room/message", json={"text": "Два"})
    assert second.status_code == 200
    assert "limit_reached" not in second.get_json()


def test_scene_photo_endpoint(app, client, user, monkeypatch):
    _patch_provider(monkeypatch)
    monkeypatch.setattr("app.routes.chat.upload_bytes", lambda data, filename, mimetype: "https://example.com/img.jpg")
    login(client)

    response = client.post(
        "/room/scene",
        data={"photo": (io.BytesIO(b"fake-image-bytes"), "table.jpg")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["reply"] == "Тестовый ответ собеседника"
    assert data["image_url"] == "https://example.com/img.jpg"
