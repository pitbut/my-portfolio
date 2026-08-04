"""Загрузка пользовательских фото через ImgBB (HTTP API).

Render не хранит файлы на диске между деплоями (эфемерная файловая система),
поэтому загруженное фото сразу пересылается на ImgBB, а в базе хранится
только вернувшаяся ссылка — как и остальные image_url в проекте, она потом
просто отображается через шаблонный image_url()."""
import requests
from flask import current_app

IMGBB_UPLOAD_URL = "https://api.imgbb.com/1/upload"
MAX_PHOTO_SIZE = 10 * 1024 * 1024  # 10 МБ — с запасом ниже лимита ImgBB (32 МБ)


def upload_photo(file_storage):
    """Загружает фото (werkzeug FileStorage из request.files) на ImgBB.

    Возвращает (url, error): url — ссылка на фото при успехе (иначе None),
    error — текст ошибки для flash при неудаче (иначе None). Если файл не
    прикреплён вовсе — тихо возвращает (None, None), фото просто необязательно."""
    if file_storage is None or not file_storage.filename:
        return None, None

    if not (file_storage.mimetype or "").startswith("image/"):
        return None, "Файл должен быть изображением."

    data = file_storage.read()
    if len(data) > MAX_PHOTO_SIZE:
        return None, "Фото слишком большое (максимум 10 МБ)."

    api_key = current_app.config.get("IMGBB_API_KEY")
    if not api_key:
        current_app.logger.warning("IMGBB_API_KEY не настроен — фото %s не загружено.", file_storage.filename)
        return None, "Загрузка фото сейчас недоступна — сохранено без фото."

    try:
        response = requests.post(
            IMGBB_UPLOAD_URL,
            params={"key": api_key},
            files={"image": (file_storage.filename, data, file_storage.mimetype)},
            timeout=20,
        )
        payload = response.json()
    except (requests.RequestException, ValueError):
        current_app.logger.exception("Не удалось загрузить фото %s на ImgBB.", file_storage.filename)
        return None, "Не удалось загрузить фото — сохранено без фото."

    if not response.ok or not payload.get("success"):
        current_app.logger.error("ImgBB отклонил фото %s: %s", file_storage.filename, payload)
        return None, "Не удалось загрузить фото — сохранено без фото."

    return payload["data"]["url"], None
