from unittest.mock import patch

from app.email import send_email


def test_send_email_returns_false_without_credentials(app):
    with app.app_context():
        assert app.config.get("MAIL_USERNAME") is None
        sent = send_email("someone@example.com", "Тема", "Текст")
        assert sent is False


def test_send_email_smtp_failure_does_not_raise(app):
    app.config["MAIL_USERNAME"] = "bot@example.com"
    app.config["MAIL_PASSWORD"] = "wrong-app-password"
    with app.app_context():
        with patch("app.email.smtplib.SMTP", side_effect=OSError("network unreachable")):
            sent = send_email("someone@example.com", "Тема", "Текст")
    assert sent is False


def test_mail_default_sender_falls_back_to_username(monkeypatch):
    monkeypatch.setenv("MAIL_USERNAME", "bot@example.com")
    monkeypatch.delenv("MAIL_DEFAULT_SENDER", raising=False)

    import importlib

    import config

    importlib.reload(config)
    assert config.Config.MAIL_DEFAULT_SENDER == "bot@example.com"

    monkeypatch.delenv("MAIL_USERNAME", raising=False)
    importlib.reload(config)


def test_mail_default_sender_falls_back_when_env_var_is_empty_string(monkeypatch):
    """Render передаёт незаданную (sync: false) переменную пустой строкой,
    а не отсутствующей — os.environ.get(..., default) в этом случае не
    подставляет значение по умолчанию, поэтому проверяем именно этот сценарий."""
    monkeypatch.setenv("MAIL_USERNAME", "bot@example.com")
    monkeypatch.setenv("MAIL_DEFAULT_SENDER", "")

    import importlib

    import config

    importlib.reload(config)
    assert config.Config.MAIL_DEFAULT_SENDER == "bot@example.com"

    monkeypatch.delenv("MAIL_USERNAME", raising=False)
    monkeypatch.delenv("MAIL_DEFAULT_SENDER", raising=False)
    importlib.reload(config)
