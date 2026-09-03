"""Публичные роуты — то, что видит обычный посетитель сайта: список
голосов (только имя и id) и озвучка текста выбранным голосом. Никаких
деталей о том, как голос был создан, здесь нет и быть не должно."""

import os
import tempfile

from flask import Blueprint, jsonify, request, send_file, after_this_request

import config
from engine import voice_store
from engine import base_tts
from engine import audio_utils
from engine.converter import convert_tone

public_bp = Blueprint("public", __name__)


@public_bp.route("/voices", methods=["GET"])
def list_voices():
    return jsonify(voice_store.list_public())


@public_bp.route("/speak", methods=["POST"])
def speak():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    voice_id = (data.get("voice_id") or "").strip()

    if not text:
        return jsonify({"error": "Пустой текст"}), 400
    if len(text) > config.MAX_TEXT_LENGTH:
        return jsonify({"error": f"Слишком длинный текст (максимум {config.MAX_TEXT_LENGTH} символов)"}), 400
    if not voice_id:
        return jsonify({"error": "Не указан voice_id"}), 400

    target_se = voice_store.get_embedding(voice_id)
    if target_se is None:
        return jsonify({"error": "Голос не найден"}), 404

    mp3_path = base_tts.synthesize(text)
    wav_path = mp3_path.replace(".mp3", ".wav")
    fd, out_path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)

    try:
        audio_utils.load_and_trim(mp3_path, wav_path, silence_thresh_db=-45)
        source_se = base_tts.get_base_speaker_embedding()
        convert_tone(wav_path, source_se, target_se, out_path, tau=config.CONVERT_TAU)
    except Exception as e:
        for p in (mp3_path, wav_path, out_path):
            if os.path.exists(p):
                os.remove(p)
        return jsonify({"error": f"Не удалось синтезировать речь: {e}"}), 500

    for p in (mp3_path, wav_path):
        if os.path.exists(p):
            os.remove(p)

    @after_this_request
    def cleanup(response):
        if os.path.exists(out_path):
            os.remove(out_path)
        return response

    return send_file(out_path, mimetype="audio/wav")
