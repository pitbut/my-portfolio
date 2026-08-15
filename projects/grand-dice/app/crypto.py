"""Шифрование чувствительных полей at rest (номер банковской карты).

Симметричное шифрование Fernet (AES-128-CBC + HMAC). Ключ — CARD_ENCRYPTION_KEY,
одна и та же строка на всех окружениях, где нужно читать уже сохранённые
данные (иначе расшифровка станет невозможна).
"""
from flask import current_app, has_app_context
from cryptography.fernet import Fernet, InvalidToken


def _resolve_key(key=None):
    if key:
        return key
    if has_app_context():
        return current_app.config.get("CARD_ENCRYPTION_KEY")
    return None


def encrypt_card_number(value, key=None):
    if not value:
        return None
    key = _resolve_key(key)
    if not key:
        raise RuntimeError(
            "CARD_ENCRYPTION_KEY не задан — установите его в .env, "
            "иначе номер карты нельзя сохранить в зашифрованном виде."
        )
    token = Fernet(key).encrypt(value.encode())
    return token.decode()


def decrypt_card_number(value, key=None):
    if not value:
        return None
    key = _resolve_key(key)
    if not key:
        return None
    try:
        return Fernet(key).decrypt(value.encode()).decode()
    except InvalidToken:
        return None
