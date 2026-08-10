"""Загрузка произвольных вложений к заявке (PDF, архивы, офисные файлы) —
не изображение, поэтому не через ImgBB (тот принимает только картинки).
Сайт развёрнут на своём VPS (не на Render с эфемерной файловой системой),
так что хранить такие файлы прямо на диске сервера надёжно — отдельная от
кода папка uploads/ рядом с app/, переживает git pull и рестарт
systemd-сервиса."""
import os
import uuid

from flask import current_app
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {"pdf", "zip", "rar", "7z", "doc", "docx", "xls", "xlsx"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 МБ


def order_uploads_dir(order_id):
    return os.path.abspath(os.path.join(current_app.root_path, "..", "uploads", "orders", str(order_id)))


def upload_order_file(file_storage, order_id):
    """Сохраняет файл в uploads/orders/<order_id>/ и возвращает (stored_name, error).

    stored_name — имя файла на диске (уникальный префикс + исходное имя,
    santized) — кладём именно его в БД, ссылку для скачивания строит
    отдельный маршрут (orders.download_attachment) через url_for. Если файл
    не прикреплён — тихо возвращает (None, None), вложение необязательно."""
    if file_storage is None or not file_storage.filename:
        return None, None

    ext = file_storage.filename.rsplit(".", 1)[-1].lower() if "." in file_storage.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        return None, "Недопустимый тип файла — разрешены PDF, ZIP, RAR, 7Z, DOC(X), XLS(X)."

    data = file_storage.read()
    if not data:
        return None, None
    if len(data) > MAX_FILE_SIZE:
        return None, "Файл слишком большой (максимум 20 МБ)."

    display_name = secure_filename(file_storage.filename) or f"file.{ext}"
    stored_name = f"{uuid.uuid4().hex}_{display_name}"

    directory = order_uploads_dir(order_id)
    os.makedirs(directory, exist_ok=True)
    with open(os.path.join(directory, stored_name), "wb") as f:
        f.write(data)

    return stored_name, None
