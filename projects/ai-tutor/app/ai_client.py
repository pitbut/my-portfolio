"""Единый клиент мультимодального ИИ-API (текст + изображения) по одному
API-ключу — раздел 6 ТЗ. Генерация программы, ведение занятия, проверка
фото решений и (в будущих версиях) определение эмоции — это разные вызовы
одного и того же провайдера (Anthropic Claude) с разными промптами."""
import base64
import json
import re

from anthropic import Anthropic
from flask import current_app

from app.prompts import EMOTION_DETECTION_PROMPT, EMOTION_LABELS, build_program_prompt


class AIClientError(RuntimeError):
    """ИИ-API не настроен или вернул ошибку."""


def _client():
    api_key = current_app.config.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise AIClientError(
            "ANTHROPIC_API_KEY не настроен — единый ИИ-API недоступен (см. .env.example)."
        )
    return Anthropic(api_key=api_key)


def _model():
    return current_app.config.get("ANTHROPIC_MODEL", "claude-sonnet-4-5")


def send_lesson_turn(system_prompt, history_messages, user_content):
    """Один вызов ведения занятия (Промпт А).

    history_messages — список {"role": "user"|"assistant", "content": ...}
    в формате, ожидаемом Anthropic Messages API (текст или список блоков).
    user_content — content нового сообщения ученика (текст или список
    блоков text+image для фото решения).

    Возвращает сырой текст ответа модели (три блока SPEECH/BOARD/STATE),
    который затем разбирает app/lesson_parser.py."""
    client = _client()
    messages = list(history_messages) + [{"role": "user", "content": user_content}]

    response = client.messages.create(
        model=_model(),
        max_tokens=2000,
        system=system_prompt,
        messages=messages,
    )
    return "".join(block.text for block in response.content if block.type == "text")


def build_photo_content(text, image_bytes, mime_type):
    """Собирает content-блок сообщения ученика с приложенным фото решения
    (мультимодальный вход — та же схема, что и текстовый диалог, раздел 6 ТЗ)."""
    return [
        {"type": "text", "text": text},
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": mime_type,
                "data": base64.b64encode(image_bytes).decode("ascii"),
            },
        },
    ]


def generate_program(subject, grade, curriculum=None):
    """Промпт Б — разовая генерация списка тем при выборе предмета/класса.

    В MVP (раздел 9.1 ТЗ) программа — фиксированный список в БД, поэтому
    в основном пользовательском потоке эта функция не вызывается: ей
    пользуется offline-скрипт scripts/generate_program.py для наполнения
    data/topics.csv перед деплоем. Возвращает список
    {"order", "title", "description"}."""
    client = _client()
    prompt = build_program_prompt(subject, grade, curriculum)

    response = client.messages.create(
        model=_model(),
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(block.text for block in response.content if block.type == "text")

    match = re.search(r"\[.*\]", text, re.S)
    if not match:
        raise AIClientError(f"Не удалось найти JSON-список тем в ответе модели: {text!r}")
    return json.loads(match.group(0))


def detect_emotion(image_bytes, mime_type):
    """Промпт В — определение эмоции ученика по кадру с камеры.

    Не используется автоматически в MVP (раздел 9.1 ТЗ: анализ эмоций —
    этап 9.3), реализовано заранее для последующих версий. Возвращает
    метку из EMOTION_LABELS или None, если модель ответила "unknown"
    (эквивалентно отсутствию сигнала — см. Промпт В)."""
    client = _client()
    response = client.messages.create(
        model=_model(),
        max_tokens=10,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": EMOTION_DETECTION_PROMPT},
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": mime_type,
                            "data": base64.b64encode(image_bytes).decode("ascii"),
                        },
                    },
                ],
            }
        ],
    )
    label = "".join(block.text for block in response.content if block.type == "text").strip().lower()
    return label if label in EMOTION_LABELS and label != "unknown" else None
