"""Отправка писем через SMTP.

Если MAIL_USERNAME не настроен (нет учётных данных SMTP), письма не
отправляются по-настоящему — вместо этого текст письма пишется в лог
приложения. Это позволяет разрабатывать и тестировать регистрацию
локально без реального почтового сервера и не роняет прод, если
администратор ещё не подключил SMTP.
"""
import smtplib
from email.message import EmailMessage

from flask import current_app


def send_email(to, subject, body):
    """Отправляет письмо или, если SMTP не настроен, пишет его в лог.

    Возвращает True, если письмо реально отправлено по SMTP, и False,
    если сработал запасной вариант (лог) — по этому флагу можно решить,
    показывать ли пользователю ссылку прямо на странице."""
    username = current_app.config.get("MAIL_USERNAME")
    password = current_app.config.get("MAIL_PASSWORD")

    if not username or not password:
        current_app.logger.warning(
            "SMTP не настроен (MAIL_USERNAME/MAIL_PASSWORD пусты). "
            "Письмо для %s не отправлено, содержимое:\n%s\n%s",
            to, subject, body,
        )
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = current_app.config["MAIL_DEFAULT_SENDER"]
    msg["To"] = to
    msg.set_content(body)

    server = current_app.config["MAIL_SERVER"]
    port = current_app.config["MAIL_PORT"]
    use_tls = current_app.config["MAIL_USE_TLS"]

    with smtplib.SMTP(server, port, timeout=10) as smtp:
        if use_tls:
            smtp.starttls()
        smtp.login(username, password)
        smtp.send_message(msg)

    return True
