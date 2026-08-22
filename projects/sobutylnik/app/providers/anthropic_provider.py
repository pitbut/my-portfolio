"""Адаптер Anthropic Claude — первый и пока единственный реализованный
провайдер универсального слоя (см. app/providers/__init__.py)."""
import base64

from anthropic import Anthropic
from flask import current_app

from app.providers.base import AIProvider, AIProviderError


class AnthropicProvider(AIProvider):
    def _client(self):
        api_key = current_app.config.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise AIProviderError(
                "ANTHROPIC_API_KEY не настроен — ИИ-собеседник недоступен (см. .env.example)."
            )
        return Anthropic(api_key=api_key)

    def _model(self):
        return current_app.config.get("ANTHROPIC_MODEL", "claude-sonnet-4-5")

    def send_message(self, system_prompt, history, user_content, max_tokens=800):
        client = self._client()
        messages = list(history) + [{"role": "user", "content": user_content}]

        response = client.messages.create(
            model=self._model(),
            max_tokens=max_tokens,
            system=system_prompt,
            messages=messages,
        )
        text = "".join(block.text for block in response.content if block.type == "text")
        usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }
        return text, usage

    def build_image_content(self, text, image_bytes, mime_type):
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
