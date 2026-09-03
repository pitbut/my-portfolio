"""Хранилище голосовых профилей.

Каждый профиль — это папка data/voices/<id>/ с двумя файлами:
  meta.json      — {id, name, created_at}   (то, что можно показывать наружу)
  embedding.pt   — тензор тембра голоса (внутреннее, наружу никогда не отдаётся)

Публичный API (routes/public_routes.py) видит только list_public() —
id и name. Как именно голос был создан (запись, обрезка тишины,
извлечение эмбеддинга) — знает только admin_routes.py.
"""

import json
import shutil
import uuid
from datetime import datetime, timezone

import config
from . import audio_utils
from .converter import extract_embedding, save_embedding, load_embedding


def _voice_dir(voice_id: str):
    return config.VOICES_DIR / voice_id


def create_voice(name: str, uploaded_audio_path: str) -> dict:
    """Принимает путь к загруженному админом аудио (любой формат, который
    понимает ffmpeg), извлекает профиль тембра и сохраняет его. Возвращает
    публичные метаданные профиля."""
    voice_id = uuid.uuid4().hex[:12]
    voice_dir = _voice_dir(voice_id)
    voice_dir.mkdir(parents=True, exist_ok=False)

    trimmed_path = voice_dir / "reference.wav"
    try:
        audio_utils.load_and_trim(uploaded_audio_path, str(trimmed_path))
        embedding = extract_embedding(str(trimmed_path))
        save_embedding(embedding, str(voice_dir / "embedding.pt"))

        meta = {
            "id": voice_id,
            "name": name,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        with open(voice_dir / "meta.json", "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        # Исходную запись-эталон после извлечения эмбеддинга не храним —
        # для клонирования она больше не нужна, а голос человека — чувствительные данные.
        trimmed_path.unlink(missing_ok=True)

        return meta
    except Exception:
        shutil.rmtree(voice_dir, ignore_errors=True)
        raise


def list_public() -> list:
    """Список голосов для обычных посетителей сайта — только id и имя."""
    voices = []
    for meta_path in sorted(config.VOICES_DIR.glob("*/meta.json")):
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)
        voices.append({"id": meta["id"], "name": meta["name"]})
    return voices


def list_admin() -> list:
    """Список для админки — то же самое плюс дата создания."""
    voices = []
    for meta_path in sorted(config.VOICES_DIR.glob("*/meta.json")):
        with open(meta_path, encoding="utf-8") as f:
            voices.append(json.load(f))
    return voices


def get_embedding(voice_id: str):
    path = _voice_dir(voice_id) / "embedding.pt"
    if not path.exists():
        return None
    return load_embedding(str(path))


def exists(voice_id: str) -> bool:
    return (_voice_dir(voice_id) / "meta.json").exists()


def delete_voice(voice_id: str) -> bool:
    voice_dir = _voice_dir(voice_id)
    if not voice_dir.exists():
        return False
    shutil.rmtree(voice_dir)
    return True
