"""Загрузка файлов книг (pdf/epub/fb2/...) для скачивания в «Библиотеке».

В отличие от фото (см. photos.py), эти файлы не уходят на внешний
хостинг — Исток работает на своём сервере с постоянным диском (не Render),
поэтому файлы просто сохраняются в instance/book_files и отдаются через
контролируемый роут скачивания."""
import os
import uuid

from flask import current_app
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {"pdf", "epub", "fb2", "djvu", "doc", "docx", "txt", "rtf", "mobi"}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 МБ — с запасом под djvu/pdf со сканами


def upload_dir():
    path = os.path.join(current_app.instance_path, "book_files")
    os.makedirs(path, exist_ok=True)
    return path


def upload_book_files(file_storages):
    """Сохраняет список файлов книги (werkzeug FileStorage) на диск.

    Возвращает (saved, errors): saved — список словарей с полями для
    создания BookFile (format/filename/original_filename/size_bytes),
    errors — список текстов ошибок для flash (файлы с недопустимым
    форматом или превышающие лимит размера просто пропускаются)."""
    saved = []
    errors = []

    for file_storage in file_storages:
        if file_storage is None or not file_storage.filename:
            continue

        original_name = secure_filename(file_storage.filename)
        ext = original_name.rsplit(".", 1)[-1].lower() if "." in original_name else ""

        if ext not in ALLOWED_EXTENSIONS:
            errors.append(f"«{file_storage.filename}»: формат .{ext or '?'} не поддерживается.")
            continue

        data = file_storage.read()
        if len(data) > MAX_FILE_SIZE:
            errors.append(f"«{file_storage.filename}»: файл слишком большой (максимум 100 МБ).")
            continue
        if not data:
            continue

        stored_name = f"{uuid.uuid4().hex}.{ext}"
        with open(os.path.join(upload_dir(), stored_name), "wb") as f:
            f.write(data)

        saved.append({
            "format": ext,
            "filename": stored_name,
            "original_filename": original_name,
            "size_bytes": len(data),
        })

    return saved, errors
