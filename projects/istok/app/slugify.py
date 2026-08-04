"""Транслитерация кириллицы в URL-безопасный slug.

Используется и в seed.py (для CSV-разделов без готовой колонки slug), и в
миграциях (для backfill slug на уже заполненных таблицах) — вынесено в один
модуль, чтобы не дублировать словарь транслитерации."""
import re

_TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}


def slugify(text, fallback="item"):
    """Транслитерация кириллицы + приведение к URL-безопасному виду."""
    lowered = (text or "").lower()
    transliterated = "".join(_TRANSLIT.get(ch, ch) for ch in lowered)
    slug = re.sub(r"[^a-z0-9]+", "-", transliterated).strip("-")
    return slug or fallback


def unique_slug(text, used_slugs, fallback="item"):
    """slugify() + де-дупликация суффиксом -2, -3... среди уже занятых slug'ов."""
    base = slugify(text, fallback)
    slug = base
    n = 2
    while slug in used_slugs:
        slug = f"{base}-{n}"
        n += 1
    used_slugs.add(slug)
    return slug
