"""Отображение сумм в других валютах — курс подтягивается с публичного API
и кэшируется. Это ТОЛЬКО отображение: все балансы, ставки и записи в БД
всегда хранятся и считаются в суммах (UZS) — курс никогда не участвует в
расчёте ставок или списании со счёта, чтобы колебания курса между загрузкой
страницы и отправкой формы не могли повлиять на баланс игрока.

Игрок выбирает валюту "для себя" (селектор в шапке, хранится в localStorage
на клиенте) — рядом с суммой в сумах JS дорисовывает эквивалент, используя
курсы, встроенные в страницу через контекст-процессор.
"""
from datetime import datetime, timedelta

import requests

FX_API_URL = "https://open.er-api.com/v6/latest/UZS"
FX_REFRESH_INTERVAL = timedelta(hours=6)
FX_REQUEST_TIMEOUT = 5

# Валюты, которые показываем рядом с суммой. UZS — базовая (курс 1),
# остальные подобраны под соседние страны и валюты из ТЗ (юань, евро,
# доллар, рубль, тенге).
SUPPORTED_CURRENCIES = {
    "UZS": {"symbol": "сум", "label": "Сум (UZS)"},
    "KZT": {"symbol": "₸", "label": "Тенге (KZT)"},
    "USD": {"symbol": "$", "label": "Доллар (USD)"},
    "RUB": {"symbol": "₽", "label": "Рубль (RUB)"},
    "CNY": {"symbol": "¥", "label": "Юань (CNY)"},
    "EUR": {"symbol": "€", "label": "Евро (EUR)"},
}

# Резервные курсы (примерные, на случай если внешний API недоступен и в
# базе ещё нет ни одного успешного обновления) — только чтобы интерфейс не
# показывал пустоту при самом первом запуске.
FALLBACK_RATES = {
    "UZS": 1.0,
    "KZT": 0.0060,
    "USD": 0.000078,
    "RUB": 0.0073,
    "CNY": 0.00056,
    "EUR": 0.000072,
}


def fetch_rates():
    """Тянет свежие курсы с внешнего API. Бросает исключение при сбое —
    вызывающий код должен подстраховаться и оставить старый кэш."""
    response = requests.get(FX_API_URL, timeout=FX_REQUEST_TIMEOUT)
    response.raise_for_status()
    data = response.json()
    if data.get("result") != "success":
        raise ValueError(f"Неожиданный ответ FX API: {data}")

    all_rates = data["rates"]
    return {code: all_rates[code] for code in SUPPORTED_CURRENCIES if code in all_rates}


def get_cached_rates():
    """Возвращает текущий словарь курсов {code: сколько единиц валюты за 1 сум},
    обновляя кэш в CasinoSettings, если он устарел или отсутствует. При
    сбое сети — тихо остаётся на последнем известном (или резервном) курсе."""
    import json

    from app import db
    from app.models import CasinoSettings

    settings = CasinoSettings.get()
    is_stale = (
        not settings.fx_rates_json
        or not settings.fx_rates_updated_at
        or datetime.utcnow() - settings.fx_rates_updated_at > FX_REFRESH_INTERVAL
    )

    if is_stale:
        try:
            rates = fetch_rates()
            settings.fx_rates_json = json.dumps(rates)
            settings.fx_rates_updated_at = datetime.utcnow()
            db.session.commit()
            return rates
        except Exception:
            db.session.rollback()
            # Не смогли обновить — используем то, что уже есть в кэше (пусть и старое).

    if settings.fx_rates_json:
        return json.loads(settings.fx_rates_json)
    return dict(FALLBACK_RATES)
