import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
VOICES_DIR = DATA_DIR / "voices"
BASE_SPEAKER_SE_PATH = DATA_DIR / "base_speaker_se.pt"

# Токен для доступа к /admin/* — задаётся через переменную окружения,
# никогда не хранится в коде. Без него админ-роуты недоступны.
ADMIN_TOKEN = os.environ.get("VOICE_ENGINE_ADMIN_TOKEN", "")

# Язык синтеза базовой озвучки Google TTS (gTTS).
TTS_LANG = os.environ.get("VOICE_ENGINE_TTS_LANG", "ru")

# tau управляет тем, насколько сильно перенимается тембр эталона:
# ближе к 0 — сильнее эффект клонирования, ближе к 1 — ближе к исходному Google-голосу.
CONVERT_TAU = float(os.environ.get("VOICE_ENGINE_TAU", "0.3"))

MAX_TEXT_LENGTH = int(os.environ.get("VOICE_ENGINE_MAX_TEXT_LENGTH", "500"))

DATA_DIR.mkdir(exist_ok=True)
VOICES_DIR.mkdir(parents=True, exist_ok=True)
