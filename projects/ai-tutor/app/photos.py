"""Загрузка фото решений через ImgBB (HTTP API).

Render не хранит файлы на диске между деплоями (эфемерная файловая
система), поэтому фото сразу пересылается на ImgBB, а в базе хранится
только вернувшаяся ссылка — она используется для отображения фото в
истории занятия. Сам анализ решения идёт по исходным байтам напрямую в
ИИ-API (app/ai_client.py), независимо от того, успешна ли загрузка на
ImgBB, — постоянное хранилище фото не обязательно для проверки."""
import requests
from flask import current_app

IMGBB_UPLOAD_URL = "https://api.imgbb.com/1/upload"
MAX_PHOTO_SIZE = 10 * 1024 * 1024  # 10 МБ — с запасом ниже лимита ImgBB (32 МБ)


def upload_photo_bytes(data, filename, mimetype):
    """Загружает байты фото на ImgBB. Возвращает URL при успехе, иначе None
    (не бросает исключение — отсутствие постоянного хранилища не должно
    прерывать проверку решения)."""
    api_key = current_app.config.get("IMGBB_API_KEY")
    if not api_key:
        current_app.logger.warning("IMGBB_API_KEY не настроен — фото %s не сохранено.", filename)
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
        current_app.logger.exception("Не удалось загрузить фото %s на ImgBB.", filename)
        return None

    if not response.ok or not payload.get("success"):
        current_app.logger.error("ImgBB отклонил фото %s: %s", filename, payload)
        return None

    return payload["data"]["url"]
