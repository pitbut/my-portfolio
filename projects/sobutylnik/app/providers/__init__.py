"""Универсальный слой ИИ-провайдеров: выбор конкретного адаптера по
конфигу AI_PROVIDER, чтобы маршруты (app/routes/chat.py) не знали, какой
именно API за ними стоит. На старте реализован только Anthropic Claude —
добавление Groq/Gemini/OpenAI как альтернативных адаптеров сводится к
новому файлу с тем же интерфейсом (см. base.py) и записи в _PROVIDERS."""
from flask import current_app

from app.providers.base import AIProviderError

_PROVIDERS = {}


def _register():
    if _PROVIDERS:
        return
    from app.providers.anthropic_provider import AnthropicProvider

    _PROVIDERS["anthropic"] = AnthropicProvider


def get_provider():
    """Возвращает экземпляр провайдера, настроенного через AI_PROVIDER."""
    _register()
    name = current_app.config.get("AI_PROVIDER", "anthropic")
    provider_cls = _PROVIDERS.get(name)
    if provider_cls is None:
        raise AIProviderError(
            f"Неизвестный AI_PROVIDER={name!r}. Доступные провайдеры: {', '.join(_PROVIDERS)}."
        )
    return provider_cls()


__all__ = ["get_provider", "AIProviderError"]
