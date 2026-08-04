"""Отправка писем через Resend (HTTP API).

Render блокирует исходящие SMTP-соединения (порты 25/465/587) на бесплатном
тарифе, поэтому письма отправляются через HTTPS-API Resend, а не через
smtplib. Если RESEND_API_KEY не настроен (нет учётных данных), письма не
отправляются по-настоящему — вместо этого текст письма пишется в лог
приложения. Это позволяет разрабатывать и тестировать регистрацию локально
без реального email-провайдера и не роняет прод, если администратор ещё не
подключил Resend.
"""
import json
import urllib.error
import urllib.request

from flask import current_app

RESEND_API_URL = "https://api.resend.com/emails"


def send_email(to, subject, body):
    """Отправляет письмо через Resend или, если API-ключ не настроен, пишет его в лог.

    Возвращает True, если письмо реально отправлено, и False, если
    сработал запасной вариант (лог) — по этому флагу можно решить,
    показывать ли пользователю ссылку прямо на странице."""
    api_key = current_app.config.get("RESEND_API_KEY")

    if not api_key:
        current_app.logger.warning(
            "Resend не настроен (RESEND_API_KEY пуст). "
            "Письмо для %s не отправлено, содержимое:\n%s\n%s",
            to, subject, body,
        )
        return False

    payload = json.dumps({
        "from": current_app.config["MAIL_DEFAULT_SENDER"],
        "to": [to],
        "subject": subject,
        "text": body,
    }).encode("utf-8")

    request = urllib.request.Request(
        RESEND_API_URL,
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            # Без нормального User-Agent запрос уходит как "Python-urllib/x.y",
            # который Cloudflare (через него идёт api.resend.com) блокирует как
            # похожий на бота — 403 "error code: 1010".
            "User-Agent": "istok-app/1.0 (+https://istok.onrender.com)",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            if not (200 <= response.status < 300):
                current_app.logger.error(
                    "Resend вернул статус %s при отправке письма для %s.", response.status, to
                )
                return False
    except urllib.error.HTTPError as exc:
        current_app.logger.error(
            "Resend отклонил письмо для %s: %s %s", to, exc.code, exc.read().decode(errors="replace")
        )
        return False
    except (urllib.error.URLError, OSError):
        current_app.logger.exception("Не удалось отправить письмо для %s через Resend.", to)
        return False

    return True
