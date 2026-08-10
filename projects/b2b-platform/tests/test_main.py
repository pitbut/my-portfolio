import os

from werkzeug.security import generate_password_hash

from app import db
from app.models import TelegramLink, User

from tests.conftest import register


def _login_via_session(client, user_id):
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user_id)
        sess["_fresh"] = True


def test_homepage_shows_registration_stats_and_constructor_cta(client):
    register(client, email="cust@example.com", role="customer")
    client.get("/auth/logout")
    register(client, email="exec@example.com", role="executor")
    client.get("/auth/logout")
    register(client, email="constr@example.com", role="constructor")
    client.get("/auth/logout")

    resp = client.get("/")
    assert resp.status_code == 200
    assert b">3<" in resp.data  # общий счётчик "зарегистрировано всего"
    assert "/profile/constructor".encode() in resp.data


def test_google_signup_user_without_telegram_sees_reminder(client):
    # Пишем через тот же db.session, что использует тестовый app-контекст
    # фикстуры (client-запросы переиспользуют этот же контекст) — иначе
    # SQLAlchemy identity map в запросах не увидит изменения, сделанные
    # через отдельный вручную поднятый app_context.
    user = User(
        email="viagoogle@example.com", google_sub="fake-google-sub-123",
        role="customer", email_confirmed=True,
    )
    db.session.add(user)
    db.session.commit()
    user_id = user.id

    _login_via_session(client, user_id)

    client.application.config["TELEGRAM_BOT_TOKEN"] = "test-token"
    client.application.config["TELEGRAM_BOT_USERNAME"] = "test_bot"
    try:
        resp = client.get("/")
        assert "привяжите Telegram".encode() in resp.data

        db.session.add(TelegramLink(user_id=user_id, telegram_chat_id=123, notifications_enabled=True))
        db.session.commit()

        resp = client.get("/")
        assert "привяжите Telegram".encode() not in resp.data
    finally:
        client.application.config["TELEGRAM_BOT_TOKEN"] = None
        client.application.config["TELEGRAM_BOT_USERNAME"] = None


def test_no_reminder_for_password_signup_user(client):
    register(client, email="viapassword@example.com", role="customer")
    client.application.config["TELEGRAM_BOT_TOKEN"] = "test-token"
    client.application.config["TELEGRAM_BOT_USERNAME"] = "test_bot"
    try:
        resp = client.get("/")
        assert "привяжите Telegram".encode() not in resp.data
    finally:
        client.application.config["TELEGRAM_BOT_TOKEN"] = None
        client.application.config["TELEGRAM_BOT_USERNAME"] = None


def test_home_page_shows_video_placeholder_and_ad_banner(client):
    """Пока администратор не залил intro.mp4 на сервер — вместо плеера
    показываем заглушку, а не сломанное видео; техническую подсказку,
    куда загружать файл, видит только сам администратор."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Здесь может быть ваша реклама".encode() in resp.data
    assert "Скоро здесь появится короткое видео".encode() in resp.data
    assert "Загрузите файл intro.mp4".encode() not in resp.data
    assert b"<video" not in resp.data


def test_home_page_shows_admin_hint_for_video_upload(client):
    admin = User(
        email="admin2@example.com", password_hash=generate_password_hash("adminpass123"),
        role="admin", email_confirmed=True,
    )
    db.session.add(admin)
    db.session.commit()
    _login_via_session(client, admin.id)

    resp = client.get("/")
    assert "Загрузите файл intro.mp4".encode() in resp.data


def test_home_page_shows_video_player_when_file_uploaded(client):
    video_dir = os.path.join(client.application.static_folder, "video")
    os.makedirs(video_dir, exist_ok=True)
    video_path = os.path.join(video_dir, "intro.mp4")
    with open(video_path, "wb") as f:
        f.write(b"fake video bytes")
    try:
        resp = client.get("/")
        assert b"<video" in resp.data
        assert "Скоро здесь появится короткое видео".encode() not in resp.data
    finally:
        os.remove(video_path)


def test_home_page_shows_admin_hint_for_ad_banner_upload(client):
    admin = User(
        email="admin3@example.com", password_hash=generate_password_hash("adminpass123"),
        role="admin", email_confirmed=True,
    )
    db.session.add(admin)
    db.session.commit()
    _login_via_session(client, admin.id)

    resp = client.get("/")
    assert "Загрузите файл banner.jpg".encode() in resp.data


def test_home_page_shows_ad_image_when_file_uploaded(client):
    ad_dir = os.path.join(client.application.static_folder, "ad")
    os.makedirs(ad_dir, exist_ok=True)
    banner_path = os.path.join(ad_dir, "banner.jpg")
    with open(banner_path, "wb") as f:
        f.write(b"fake image bytes")
    try:
        resp = client.get("/")
        assert 'src="/static/ad/banner.jpg"'.encode() in resp.data
        assert b"home-banner__ad-text" not in resp.data
    finally:
        os.remove(banner_path)
