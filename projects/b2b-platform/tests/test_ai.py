"""app/ai.py — единая обёртка над LLM: провайдер выбирается конфигом, без
переписывания кода при смене (см. комментарий в app/ai.py). Тесты мокают
сам HTTP-вызов (как в test_telegram_and_subscriptions.py для FCM), не
настоящую сеть."""
import requests


def test_ai_unavailable_without_api_key(client):
    client.application.config["AI_API_KEY"] = None
    with client.application.app_context():
        from app.ai import ai_available, ai_complete

        assert ai_available() is False
        assert ai_complete("system", "user") is None


def test_ai_complete_uses_anthropic_by_default(client, monkeypatch):
    client.application.config["AI_API_KEY"] = "fake-anthropic-key"
    client.application.config["AI_PROVIDER"] = "anthropic"
    client.application.config["AI_MODEL"] = None

    sent = []

    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"content": [{"type": "text", "text": "Подходит исполнитель Иванов."}]}

    def fake_post(url, headers=None, json=None, timeout=None):
        sent.append((url, headers, json))
        return FakeResponse()

    monkeypatch.setattr("app.ai.requests.post", fake_post)

    with client.application.app_context():
        from app.ai import ai_complete

        result = ai_complete("Ты помощник поиска.", "Нужен ремонт колбасного оборудования.")

    assert result == "Подходит исполнитель Иванов."
    assert len(sent) == 1
    url, headers, json_body = sent[0]
    assert url == "https://api.anthropic.com/v1/messages"
    assert headers["x-api-key"] == "fake-anthropic-key"
    assert json_body["model"] == "claude-haiku-4-5-20251001"
    assert json_body["system"] == "Ты помощник поиска."
    assert json_body["messages"] == [{"role": "user", "content": "Нужен ремонт колбасного оборудования."}]


def test_ai_complete_switches_to_openai_compatible_via_config(client, monkeypatch):
    """Смена провайдера — только конфиг, ни строчки кода: тот же ai_complete()
    вызывающий код не меняется вообще."""
    client.application.config["AI_API_KEY"] = "fake-openai-key"
    client.application.config["AI_PROVIDER"] = "openai_compatible"
    client.application.config["AI_MODEL"] = "deepseek-chat"
    client.application.config["AI_BASE_URL"] = "https://api.deepseek.com/v1"

    sent = []

    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": "Match found."}}]}

    def fake_post(url, headers=None, json=None, timeout=None):
        sent.append((url, headers, json))
        return FakeResponse()

    monkeypatch.setattr("app.ai.requests.post", fake_post)

    with client.application.app_context():
        from app.ai import ai_complete

        result = ai_complete("system prompt", "user prompt")

    assert result == "Match found."
    url, headers, json_body = sent[0]
    assert url == "https://api.deepseek.com/v1/chat/completions"
    assert headers["Authorization"] == "Bearer fake-openai-key"
    assert json_body["model"] == "deepseek-chat"
    assert json_body["messages"][0] == {"role": "system", "content": "system prompt"}


def test_ai_complete_returns_none_on_provider_error(client, monkeypatch):
    client.application.config["AI_API_KEY"] = "fake-key"
    client.application.config["AI_PROVIDER"] = "anthropic"

    def fake_post(url, headers=None, json=None, timeout=None):
        raise requests.RequestException("network down")

    monkeypatch.setattr("app.ai.requests.post", fake_post)

    with client.application.app_context():
        from app.ai import ai_complete

        assert ai_complete("system", "user") is None
