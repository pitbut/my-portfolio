"""Фиксированный набор аватаров для выбора при первом входе (раздел 4.1 ТЗ,
этап 9.2: "Аватар с анимацией и TTS-озвучкой, выбор голоса"). Голос
подбирается отдельно на клиенте из голосов, доступных в браузере ученика
(Web Speech API) — здесь хранится только визуальный образ и имя, которое
подставляется в системный промпт репетитора как {avatar_name}."""

AVATAR_CHOICES = [
    {"key": "alex", "name": "Алекс", "emoji": "🦉", "color": "#7c9cff", "has_beard": False},
    {"key": "nova", "name": "Нова", "emoji": "🦊", "color": "#ffb454", "has_beard": False},
    {"key": "leo", "name": "Лео", "emoji": "🐯", "color": "#f87171", "has_beard": False},
    {"key": "mira", "name": "Мира", "emoji": "🐬", "color": "#4ade80", "has_beard": False},
    # Оригинальный персонаж, без отсылок к каким-либо мультфильмам — седой
    # мудрый наставник с бородой (по запросу пользователя).
    {"key": "kuzmich", "name": "Кузьмич", "emoji": "🧙", "color": "#94a3b8", "has_beard": True},
]

AVATARS_BY_KEY = {a["key"]: a for a in AVATAR_CHOICES}


def get_avatar(key):
    """Возвращает описание аватара по ключу, либо первый из списка по умолчанию."""
    return AVATARS_BY_KEY.get(key, AVATAR_CHOICES[0])
