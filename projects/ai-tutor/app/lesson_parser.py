"""Разбор ответа ИИ-репетитора на три блока SPEECH/BOARD/STATE — раздел 8
Промпта А (ai-tutor-system-prompt.md). Учебный движок (lesson_engine.py)
использует эти поля, чтобы обновить доску, историю чата и прогресс ученика."""
import re

SECTION_RE = re.compile(
    r"^(SPEECH|BOARD|STATE):[ \t]*(.*?)(?=^(?:SPEECH|BOARD|STATE):|\Z)",
    re.MULTILINE | re.DOTALL,
)

STATE_KEYS = ("stage", "topic_status", "awaiting", "next_lesson_min_offset_hours")

# Модель иногда нарушает инструкцию "без markdown-разметки" в SPEECH (раздел 8
# промпта) — чаще всего звёздочками-разделителями между смысловыми частями
# реплики. Раз текст SPEECH идёт прямиком в speechSynthesis, такой символ
# озвучивается вслух буквально ("звёздочка"), поэтому подчищаем на разборе
# ответа, а не полагаемся только на соблюдение модели.
_MD_HR_RE = re.compile(r"^[ \t]*([*_-])(?:[ \t]*\1){2,}[ \t]*$", re.MULTILINE)
_MD_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_MD_UNDERSCORE_BOLD_RE = re.compile(r"__(.+?)__")
_MD_BACKTICK_RE = re.compile(r"`([^`]*)`")
_MD_HEADER_RE = re.compile(r"^[ \t]*#{1,6}[ \t]*", re.MULTILINE)


def _strip_markdown(text):
    """Убирает распространённую markdown-разметку из устной реплики (в первую
    очередь **жирный** как псевдо-заголовки между смысловыми частями — ученик
    слышит буквальное "звёздочка звёздочка", если это не убрать). Одиночную
    "*" намеренно не трогаем — в SPEECH попадаются знаки умножения."""
    if not text:
        return text
    text = _MD_HR_RE.sub("", text)
    text = _MD_BOLD_RE.sub(r"\1", text)
    text = _MD_UNDERSCORE_BOLD_RE.sub(r"\1", text)
    text = _MD_BACKTICK_RE.sub(r"\1", text)
    text = _MD_HEADER_RE.sub("", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


class ParsedLessonTurn:
    """Результат разбора одного ответа модели."""

    def __init__(self, speech, board_type, board_content, state):
        self.speech = speech
        self.board_type = board_type
        self.board_content = board_content
        self.state = state  # dict с ключами из STATE_KEYS

    @property
    def stage(self):
        return self.state.get("stage")

    @property
    def topic_status(self):
        return self.state.get("topic_status")

    @property
    def awaiting(self):
        return self.state.get("awaiting")

    @property
    def next_lesson_min_offset_hours(self):
        value = self.state.get("next_lesson_min_offset_hours")
        try:
            return int(value)
        except (TypeError, ValueError):
            return None


def _parse_board(raw):
    raw = (raw or "").strip()
    if not raw or raw.lower() == "none":
        return None, None

    type_match = re.search(r"type:\s*(\S+)", raw)
    board_type = type_match.group(1).strip() if type_match else None

    content_match = re.search(r"content:\s*(.*)", raw, re.DOTALL)
    board_content = content_match.group(1).strip() if content_match else raw

    return board_type, board_content


def _parse_state(raw):
    state = {}
    current_key = None
    for line in (raw or "").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        match = re.match(r"([a-z_]+)\s*:\s*(.*)", stripped)
        if match and match.group(1) in STATE_KEYS:
            current_key = match.group(1)
            state[current_key] = match.group(2).strip()
        elif current_key:
            # Продолжение значения, перенесённого на следующую строку
            # (см. пример многострочного stage в ТЗ).
            state[current_key] = (state[current_key] + " " + stripped).strip()
    return state


def parse_lesson_turn(raw_text):
    """Разбирает сырой текст ответа модели на SPEECH/BOARD/STATE.

    Если модель не выдержала формат (например, ответила простым текстом
    без меток) — считаем весь текст репликой, доску и state оставляем
    пустыми, чтобы диалог не падал."""
    sections = {}
    for match in SECTION_RE.finditer(raw_text or ""):
        sections[match.group(1)] = match.group(2)

    if not sections:
        return ParsedLessonTurn(
            speech=_strip_markdown((raw_text or "").strip()), board_type=None, board_content=None, state={}
        )

    speech = _strip_markdown(sections.get("SPEECH", "").strip())
    board_type, board_content = _parse_board(sections.get("BOARD", ""))
    state = _parse_state(sections.get("STATE", ""))

    return ParsedLessonTurn(speech=speech, board_type=board_type, board_content=board_content, state=state)
