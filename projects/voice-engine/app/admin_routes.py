"""Закрытые роуты управления голосами. Обычный посетитель сайта их не
видит и не вызывает — этим пользуется только панель администратора."""

import hmac
import os
import tempfile
from functools import wraps

from flask import Blueprint, jsonify, request

import config
from engine import voice_store

admin_bp = Blueprint("admin", __name__)


def require_admin_token(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not config.ADMIN_TOKEN:
            return jsonify({"error": "Админ-доступ не настроен (VOICE_ENGINE_ADMIN_TOKEN не задан)"}), 503

        token = request.headers.get("X-Admin-Token", "")
        if not hmac.compare_digest(token, config.ADMIN_TOKEN):
            return jsonify({"error": "unauthorized"}), 401

        return view(*args, **kwargs)

    return wrapped


@admin_bp.route("/voices", methods=["GET"])
@require_admin_token
def list_voices():
    return jsonify(voice_store.list_admin())


@admin_bp.route("/voices", methods=["POST"])
@require_admin_token
def add_voice():
    name = (request.form.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Укажите имя голоса"}), 400

    audio_file = request.files.get("audio")
    if audio_file is None or audio_file.filename == "":
        return jsonify({"error": "Прикрепите аудиофайл с записью голоса (лучше 1-3 минуты чистой речи)"}), 400

    suffix = os.path.splitext(audio_file.filename)[1] or ".wav"
    fd, tmp_path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    audio_file.save(tmp_path)

    try:
        meta = voice_store.create_voice(name, tmp_path)
        return jsonify(meta), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Не удалось обработать запись: {e}"}), 500
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@admin_bp.route("/voices/<voice_id>", methods=["DELETE"])
@require_admin_token
def remove_voice(voice_id):
    if voice_store.delete_voice(voice_id):
        return jsonify({"ok": True})
    return jsonify({"error": "not found"}), 404
