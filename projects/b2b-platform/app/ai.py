"""Единая обёртка над LLM для будущих «умных» функций (подбор исполнителя
по вольному описанию заявки, семантический поиск по барахолке и т.п.).

Провайдер не захардкожен — выбирается конфигом (AI_PROVIDER), чтобы смену
на более дешёвого можно было сделать одной правкой .env, без изменений в
коде. Два адаптера покрывают почти весь рынок:

  anthropic         — родной Messages API Anthropic.
  openai_compatible — формат Chat Completions, которого держится OpenAI и
                      большинство дешёвых/открытых провайдеров (DeepSeek,
                      Groq, Together, Mistral, локальный Ollama и т.п.) —
                      для них меняется только AI_BASE_URL/AI_MODEL/AI_API_KEY.

Как и с Telegram/ImgBB/Resend — без ключа ai_complete() просто возвращает
None (честная деградация), вызывающий код сам решает, что показать вместо
ИИ-результата (например, обычный фильтр без семантического дополнения)."""
import requests
from flask import current_app

DEFAULT_MODELS = {
    "anthropic": "claude-haiku-4-5-20251001",
    "openai_compatible": "gpt-4o-mini",
}


def ai_available():
    return bool(current_app.config.get("AI_API_KEY"))


def ai_complete(system_prompt, user_prompt, max_tokens=1024):
    """Возвращает текст ответа модели или None — если ключ не настроен, или
    провайдер вернул ошибку (сеть, лимиты, неверный ключ и т.п.). Ошибки
    логируются, но не всплывают наружу — ИИ-подсказка необязательна для
    работы сайта, в отличие от самого поиска/подбора."""
    if not ai_available():
        return None

    provider = current_app.config.get("AI_PROVIDER") or "anthropic"
    try:
        if provider == "anthropic":
            return _anthropic_complete(system_prompt, user_prompt, max_tokens)
        return _openai_compatible_complete(system_prompt, user_prompt, max_tokens)
    except (requests.RequestException, KeyError, IndexError, ValueError, TypeError):
        current_app.logger.exception("Ошибка обращения к AI-провайдеру (%s).", provider)
        return None


def _anthropic_complete(system_prompt, user_prompt, max_tokens):
    api_key = current_app.config["AI_API_KEY"]
    model = current_app.config.get("AI_MODEL") or DEFAULT_MODELS["anthropic"]

    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": model,
            "max_tokens": max_tokens,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        },
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    text = "".join(block.get("text", "") for block in data.get("content", []) if block.get("type") == "text")
    return text.strip() or None


def _openai_compatible_complete(system_prompt, user_prompt, max_tokens):
    api_key = current_app.config["AI_API_KEY"]
    model = current_app.config.get("AI_MODEL") or DEFAULT_MODELS["openai_compatible"]
    base_url = (current_app.config.get("AI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")

    response = requests.post(
        f"{base_url}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        },
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    text = data["choices"][0]["message"]["content"]
    return text.strip() or None
