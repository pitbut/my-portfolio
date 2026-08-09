"""Push-уведомления в мобильное приложение через Firebase Cloud Messaging
(модуль 7) — второй канал рядом с Telegram (см. app/telegram_bot.py),
подключается независимо.

Без FIREBASE_SERVICE_ACCOUNT_JSON пуши не отправляются по-настоящему —
как и с остальными внешними интеграциями в проекте (Resend/ImgBB/Telegram),
это не заглушка, а нормальная деградация: in-app уведомления и Telegram
продолжают работать."""
import json
import time

import requests
from authlib.jose import jwt

FCM_SCOPE = "https://www.googleapis.com/auth/firebase.messaging"
TOKEN_URL = "https://oauth2.googleapis.com/token"

_token_cache = {"access_token": None, "expires_at": 0}


def _service_account():
    from flask import current_app

    raw = current_app.config.get("FIREBASE_SERVICE_ACCOUNT_JSON")
    if not raw:
        return None
    try:
        return json.loads(raw)
    except ValueError:
        current_app.logger.warning("FIREBASE_SERVICE_ACCOUNT_JSON содержит невалидный JSON.")
        return None


def _get_access_token(account):
    from flask import current_app

    now = time.time()
    if _token_cache["access_token"] and _token_cache["expires_at"] > now + 30:
        return _token_cache["access_token"]

    header = {"alg": "RS256", "typ": "JWT"}
    payload = {
        "iss": account["client_email"],
        "scope": FCM_SCOPE,
        "aud": TOKEN_URL,
        "iat": int(now),
        "exp": int(now) + 3600,
    }
    assertion = jwt.encode(header, payload, account["private_key"]).decode("utf-8")

    try:
        resp = requests.post(
            TOKEN_URL,
            data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": assertion},
            timeout=10,
        )
    except requests.RequestException:
        current_app.logger.exception("Не удалось получить access token для FCM.")
        return None

    if resp.status_code != 200:
        current_app.logger.warning("Ошибка получения access token FCM (%s): %s", resp.status_code, resp.text[:200])
        return None

    data = resp.json()
    _token_cache["access_token"] = data["access_token"]
    _token_cache["expires_at"] = now + data.get("expires_in", 3600)
    return _token_cache["access_token"]


def _absolute_url(url):
    if not url:
        return ""
    if url.startswith("http://") or url.startswith("https://"):
        return url
    from flask import current_app, has_request_context, request

    if has_request_context():
        return request.url_root.rstrip("/") + url
    base = current_app.config.get("PUBLIC_BASE_URL")
    return (base.rstrip("/") + url) if base else url


def send_push(device_token, title, body=None, url=None):
    """Возвращает True, если push реально отправлен через FCM."""
    from flask import current_app

    account = _service_account()
    if account is None:
        current_app.logger.warning("FIREBASE_SERVICE_ACCOUNT_JSON не настроен — push не отправлен: %s", title[:120])
        return False

    access_token = _get_access_token(account)
    if access_token is None:
        return False

    message = {
        "message": {
            "token": device_token,
            "notification": {"title": title, "body": body or ""},
            "data": {"url": _absolute_url(url)},
        }
    }
    try:
        resp = requests.post(
            f"https://fcm.googleapis.com/v1/projects/{account['project_id']}/messages:send",
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
            json=message, timeout=10,
        )
    except requests.RequestException:
        current_app.logger.exception("Ошибка обращения к FCM.")
        return False

    if resp.status_code != 200:
        current_app.logger.warning("Ошибка отправки push (%s): %s", resp.status_code, resp.text[:200])
        # Токен могли отозвать (переустановка приложения, разлогин) — чистим,
        # чтобы не пытаться слать туда снова каждый раз.
        if resp.status_code in (400, 404):
            _forget_token(device_token)
        return False
    return True


def _forget_token(device_token):
    from app import db
    from app.models import PushDeviceToken

    PushDeviceToken.query.filter_by(token=device_token).delete()
    db.session.commit()


def send_push_to_user(user, title, body=None, url=None):
    """Шлёт на все устройства пользователя, возвращает True если хотя бы
    на одно ушло успешно."""
    sent_any = False
    for device in user.push_tokens:
        if send_push(device.token, title, body, url):
            sent_any = True
    return sent_any
