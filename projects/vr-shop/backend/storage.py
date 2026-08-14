"""
Хранилище для 3D-моделей, загруженных продавцами.

На Render диск эфемерный — файлы в uploads/ пропадают при редеплое.
Поэтому если заданы переменные окружения R2_*, файлы грузятся в
Cloudflare R2 (S3-совместимое хранилище, бесплатный тариф хватает
с запасом для GLB-моделей) и в БД сохраняется публичный URL.
Если переменные не заданы (локальная разработка) — файл просто
сохраняется на диск, как раньше.
"""
import os
import boto3
from botocore.client import Config

R2_ACCOUNT_ID = os.environ.get("R2_ACCOUNT_ID")
R2_ACCESS_KEY = os.environ.get("R2_ACCESS_KEY")
R2_SECRET_KEY = os.environ.get("R2_SECRET_KEY")
R2_BUCKET = os.environ.get("R2_BUCKET")
R2_PUBLIC_URL = os.environ.get("R2_PUBLIC_URL")  # например https://models.robutpit.com

storage_enabled = all([R2_ACCOUNT_ID, R2_ACCESS_KEY, R2_SECRET_KEY, R2_BUCKET, R2_PUBLIC_URL])

_client = None
if storage_enabled:
    _client = boto3.client(
        "s3",
        endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=R2_ACCESS_KEY,
        aws_secret_access_key=R2_SECRET_KEY,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


def upload_model(file_storage, stored_name):
    """Загружает файл в R2 и возвращает публичный URL, либо None если R2 не настроен."""
    if not storage_enabled:
        return None
    _client.upload_fileobj(
        file_storage, R2_BUCKET, stored_name,
        ExtraArgs={"ContentType": "model/gltf-binary"},
    )
    return f"{R2_PUBLIC_URL.rstrip('/')}/{stored_name}"
