"""Базовая озвучка текста через gTTS (бесплатный Google Speech).
Даёт правильное произношение и интонацию/ритм речи — тембр этого голоса
затем заменяется converter.convert_tone() на голос из выбранного профиля."""

import os
import tempfile

from gtts import gTTS

from . import audio_utils
from .converter import extract_embedding, load_embedding, save_embedding
import config

_BASE_SPEAKER_TEXT = "Здравствуйте, это проверка голоса."


def synthesize(text: str, lang: str = None) -> str:
    """Генерирует речь через gTTS и возвращает путь к временному mp3-файлу.
    Вызывающий код отвечает за удаление файла после использования."""
    lang = lang or config.TTS_LANG
    fd, path = tempfile.mkstemp(suffix=".mp3")
    os.close(fd)
    gTTS(text=text, lang=lang).save(path)
    return path


def get_base_speaker_embedding():
    """Эмбеддинг тембра самого Google TTS (source_se для convert()).
    Считается один раз и кэшируется на диск — он не зависит от текста,
    только от голоса/языка gTTS, поэтому пересчитывать его на каждый
    запрос не нужно."""
    if config.BASE_SPEAKER_SE_PATH.exists():
        return load_embedding(str(config.BASE_SPEAKER_SE_PATH))

    mp3_path = synthesize(_BASE_SPEAKER_TEXT)
    wav_path = mp3_path.replace(".mp3", ".wav")
    try:
        audio_utils.load_and_trim(mp3_path, wav_path)
        embedding = extract_embedding(wav_path)
        save_embedding(embedding, str(config.BASE_SPEAKER_SE_PATH))
        return embedding
    finally:
        for p in (mp3_path, wav_path):
            if os.path.exists(p):
                os.remove(p)
