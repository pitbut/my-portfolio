"""Разбор ответа ИИ-репетитора на три блока SPEECH/BOARD/STATE — раздел 8
Промпта А (ai-tutor-system-prompt.md). Учебный движок (lesson_engine.py)
использует эти поля, чтобы обновить доску, историю чата и прогресс ученика."""
import re

SECTION_RE = re.compile(
    r"^(SPEECH|BOARD|STATE):[ \t]*(.*?)(?=^(?:SPEECH|BOARD|STATE):|\Z)",
    re.MULTILINE | re.DOTALL,
)

STATE_KEYS = ("stage", "topic_status", "awaiting", "next_lesson_min_offset_hours")


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
        return ParsedLessonTurn(speech=(raw_text or "").strip(), board_type=None, board_content=None, state={})

    speech = sections.get("SPEECH", "").strip()
    board_type, board_content = _parse_board(sections.get("BOARD", ""))
    state = _parse_state(sections.get("STATE", ""))

    return ParsedLessonTurn(speech=speech, board_type=board_type, board_content=board_content, state=state)
