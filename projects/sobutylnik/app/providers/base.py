"""Абстрактный интерфейс ИИ-провайдера — единая точка входа, через которую
маршруты просят текстовый ответ или анализ фото, не зная, чей это API."""
from abc import ABC, abstractmethod


class AIProviderError(RuntimeError):
    """Провайдер не настроен (нет ключа) или вернул ошибку."""


class AIProvider(ABC):
    @abstractmethod
    def send_message(self, system_prompt, history, user_content, max_tokens=800):
        """Отправляет реплику пользователя с историей диалога.

        history — список {"role": "user"|"assistant", "content": ...}.
        user_content — текст новой реплики пользователя, либо список
        content-блоков text+image (см. build_image_content).

        Возвращает (text, usage) — usage: {"input_tokens", "output_tokens"}."""

    @abstractmethod
    def build_image_content(self, text, image_bytes, mime_type):
        """Собирает мультимодальный content-блок (текст + изображение) для
        передачи в send_message как user_content — используется для "фото
        обстановки" (камера/загруженное фото стола/компании)."""
