"""Обёртка над openvoice-cli (OpenVoice V2 tone-color converter).

Важно: мы НЕ используем встроенные в openvoice_cli функции сегментации
референса (se_extractor.get_se с vad=True/False) — они тянут либо Silero VAD
через torch.hub (нужен доступ к github.com), либо faster-whisper с
device="cuda" (упадёт без GPU). Вместо этого сами извлекаем эмбеддинг
голоса через ToneColorConverter.extract_se() напрямую на уже обрезанном
(engine.audio_utils.load_and_trim) файле — это единственное, что реально
нужно для клонирования тембра, и оно полностью работает на CPU.
"""

import os
import threading

import torch
from openvoice_cli.api import ToneColorConverter
from openvoice_cli.downloader import download_checkpoint

_lock = threading.Lock()
_converter = None


def _checkpoint_dir() -> str:
    import openvoice_cli
    return os.path.join(os.path.dirname(openvoice_cli.__file__), "checkpoints", "converter")


def get_converter() -> ToneColorConverter:
    """Ленивая загрузка модели (один раз на процесс). Первый вызов на новой
    машине скачает чекпоинт (~130 МБ) с HuggingFace."""
    global _converter
    if _converter is not None:
        return _converter

    with _lock:
        if _converter is not None:
            return _converter

        ckpt_dir = _checkpoint_dir()
        if not os.path.exists(os.path.join(ckpt_dir, "checkpoint.pth")):
            os.makedirs(ckpt_dir, exist_ok=True)
            download_checkpoint(ckpt_dir)

        converter = ToneColorConverter(os.path.join(ckpt_dir, "config.json"), device="cpu")
        converter.load_ckpt(os.path.join(ckpt_dir, "checkpoint.pth"))
        _converter = converter
        return _converter


def extract_embedding(wav_path: str):
    """Возвращает тензор-эмбеддинг тембра голоса из одного wav-файла."""
    converter = get_converter()
    return converter.extract_se([wav_path])


def save_embedding(embedding, path: str) -> None:
    torch.save(embedding.cpu(), path)


def load_embedding(path: str):
    return torch.load(path, map_location="cpu")


def convert_tone(source_wav: str, source_se, target_se, output_wav: str, tau: float = 0.3) -> str:
    converter = get_converter()
    converter.convert(
        audio_src_path=source_wav,
        src_se=source_se,
        tgt_se=target_se,
        output_path=output_wav,
        tau=tau,
    )
    return output_wav
