import urllib.error
from unittest.mock import MagicMock, patch

from app.email import send_email


def test_send_email_returns_false_without_api_key(app):
    with app.app_context():
        assert app.config.get("RESEND_API_KEY") is None
        sent = send_email("someone@example.com", "Тема", "Текст")
        assert sent is False


def test_send_email_success(app):
    app.config["RESEND_API_KEY"] = "re_test_key"
    with app.app_context():
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__.return_value = mock_response
        with patch("app.email.urllib.request.urlopen", return_value=mock_response):
            sent = send_email("someone@example.com", "Тема", "Текст")
    assert sent is True


def test_send_email_http_error_does_not_raise(app):
    app.config["RESEND_API_KEY"] = "re_test_key"
    with app.app_context():
        error = urllib.error.HTTPError(
            "https://api.resend.com/emails", 401, "Unauthorized", {}, None
        )
        error.read = lambda: b'{"message": "invalid api key"}'
        with patch("app.email.urllib.request.urlopen", side_effect=error):
            sent = send_email("someone@example.com", "Тема", "Текст")
    assert sent is False


def test_send_email_network_error_does_not_raise(app):
    app.config["RESEND_API_KEY"] = "re_test_key"
    with app.app_context():
        with patch(
            "app.email.urllib.request.urlopen",
            side_effect=urllib.error.URLError("network unreachable"),
        ):
            sent = send_email("someone@example.com", "Тема", "Текст")
    assert sent is False


def test_mail_default_sender_falls_back_to_resend_default(monkeypatch):
    monkeypatch.delenv("MAIL_DEFAULT_SENDER", raising=False)

    import importlib

    import config

    importlib.reload(config)
    assert config.Config.MAIL_DEFAULT_SENDER == "Исток <onboarding@resend.dev>"


def test_mail_default_sender_falls_back_when_env_var_is_empty_string(monkeypatch):
    """Render передаёт незаданную (sync: false) переменную пустой строкой,
    а не отсутствующей — os.environ.get(..., default) в этом случае не
    подставляет значение по умолчанию, поэтому проверяем именно этот сценарий."""
    monkeypatch.setenv("MAIL_DEFAULT_SENDER", "")

    import importlib

    import config

    importlib.reload(config)
    assert config.Config.MAIL_DEFAULT_SENDER == "Исток <onboarding@resend.dev>"

    monkeypatch.delenv("MAIL_DEFAULT_SENDER", raising=False)
    importlib.reload(config)
