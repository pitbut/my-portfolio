"""Загрузка фото для переписки поддержки.

Файлы хранятся на диске сервера в instance/uploads/support/ (вне git, вне
static/ — не публично раздаются напрямую, доступ только через
авторизованный маршрут /support/photo/<id>, см. app/routes/support.py).
"""
import os
import uuid

from flask import current_app
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif"}
MAX_PHOTO_BYTES = 5 * 1024 * 1024  # 5 МБ


def _extension(filename):
    if "." not in filename:
        return None
    return filename.rsplit(".", 1)[1].lower()


def support_upload_dir():
    path = os.path.join(current_app.instance_path, "uploads", "support")
    os.makedirs(path, exist_ok=True)
    return path


def save_support_photo(file_storage):
    """Сохраняет загруженное фото и возвращает имя файла на диске.

    Возвращает None, если файл не передан. Бросает ValueError при
    недопустимом расширении или превышении размера.
    """
    if not file_storage or not file_storage.filename:
        return None

    original_name = secure_filename(file_storage.filename)
    ext = _extension(original_name)
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError("Допустимые форматы фото: jpg, png, webp, gif.")

    file_storage.seek(0, os.SEEK_END)
    size = file_storage.tell()
    file_storage.seek(0)
    if size > MAX_PHOTO_BYTES:
        raise ValueError("Файл слишком большой (максимум 5 МБ).")

    stored_name = f"{uuid.uuid4().hex}.{ext}"
    file_storage.save(os.path.join(support_upload_dir(), stored_name))
    return stored_name


def support_photo_path(filename):
    return os.path.join(support_upload_dir(), filename)
