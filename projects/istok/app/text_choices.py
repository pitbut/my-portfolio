"""Небольшая утилита для полей вроде «жанр»/«рубрика»: чтобы одно и то же
значение, введённое с разным регистром или лишним пробелом (например,
«Роман» и «роман»), не плодило дубли в базе."""


def match_existing(value, choices):
    """Если среди choices есть строка, совпадающая с value без учёта
    регистра, возвращает её (сохраняя уже принятое в базе написание) —
    иначе возвращает value как новый вариант."""
    value = (value or "").strip()
    if not value:
        return None
    for choice in choices:
        if choice.lower() == value.lower():
            return choice
    return value
