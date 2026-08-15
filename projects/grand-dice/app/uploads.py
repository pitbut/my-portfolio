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

ALLOWED_RECEIPT_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "pdf"}
MAX_RECEIPT_BYTES = 8 * 1024 * 1024  # 8 МБ


def _extension(filename):
    if "." not in filename:
        return None
    return filename.rsplit(".", 1)[1].lower()


def _save_upload(file_storage, subdir, allowed_extensions, max_bytes, error_hint):
    if not file_storage or not file_storage.filename:
        return None

    original_name = secure_filename(file_storage.filename)
    ext = _extension(original_name)
    if ext not in allowed_extensions:
        raise ValueError(f"Допустимые форматы: {error_hint}.")

    file_storage.seek(0, os.SEEK_END)
    size = file_storage.tell()
    file_storage.seek(0)
    if size > max_bytes:
        raise ValueError(f"Файл слишком большой (максимум {max_bytes // (1024 * 1024)} МБ).")

    path = os.path.join(current_app.instance_path, "uploads", subdir)
    os.makedirs(path, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}.{ext}"
    file_storage.save(os.path.join(path, stored_name))
    return stored_name


def support_upload_dir():
    path = os.path.join(current_app.instance_path, "uploads", "support")
    os.makedirs(path, exist_ok=True)
    return path


def save_support_photo(file_storage):
    """Сохраняет загруженное фото и возвращает имя файла на диске.

    Возвращает None, если файл не передан. Бросает ValueError при
    недопустимом расширении или превышении размера.
    """
    return _save_upload(file_storage, "support", ALLOWED_EXTENSIONS, MAX_PHOTO_BYTES, "jpg, png, webp, gif")


def support_photo_path(filename):
    return os.path.join(support_upload_dir(), filename)


def receipt_upload_dir():
    path = os.path.join(current_app.instance_path, "uploads", "receipts")
    os.makedirs(path, exist_ok=True)
    return path


def save_receipt_file(file_storage):
    """Сохраняет чек об оплате (фото или PDF), приложенный к заявке на
    пополнение. Возвращает None, если файл не передан."""
    return _save_upload(
        file_storage, "receipts", ALLOWED_RECEIPT_EXTENSIONS, MAX_RECEIPT_BYTES, "jpg, png, webp, pdf"
    )


def receipt_path(filename):
    return os.path.join(receipt_upload_dir(), filename)
