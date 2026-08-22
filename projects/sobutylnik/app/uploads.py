"""Загрузка файлов через ImgBB (HTTP API).

Render не хранит файлы на диске между деплоями (эфемерная файловая
система), поэтому вложения (фото обстановки в комнате, файлы в чате
поддержки) сразу пересылаются на ImgBB, а сохраняется только вернувшаяся
ссылка. Если IMGBB_API_KEY не настроен — вложение не сохраняется
постоянно (не бросает исключение, вызывающий код решает, что делать)."""
import requests
from flask import current_app

IMGBB_UPLOAD_URL = "https://api.imgbb.com/1/upload"
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 МБ — с запасом ниже лимита ImgBB (32 МБ)


def upload_bytes(data, filename, mimetype):
    """Загружает байты на ImgBB. Возвращает URL при успехе, иначе None."""
    api_key = current_app.config.get("IMGBB_API_KEY")
    if not api_key:
        current_app.logger.warning("IMGBB_API_KEY не настроен — файл %s не сохранён.", filename)
        return None

    try:
        response = requests.post(
            IMGBB_UPLOAD_URL,
            params={"key": api_key},
            files={"image": (filename, data, mimetype)},
            timeout=20,
        )
        payload = response.json()
    except (requests.RequestException, ValueError):
        current_app.logger.exception("Не удалось загрузить файл %s на ImgBB.", filename)
        return None

    if not response.ok or not payload.get("success"):
        current_app.logger.error("ImgBB отклонил файл %s: %s", filename, payload)
        return None

    return payload["data"]["url"]
