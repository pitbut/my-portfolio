from app.lesson_parser import parse_lesson_turn

SAMPLE_RESPONSE = """SPEECH: Привет, Аня! Сегодня разберём обыкновенные дроби.

BOARD:
type: text
content: Тема: Обыкновенные дроби

STATE:
stage: explanation
topic_status: in_progress
awaiting: none
next_lesson_min_offset_hours: 3
"""

NO_BOARD_RESPONSE = """SPEECH: Отлично, ты справился со всеми заданиями!
BOARD: none
STATE:
stage: lesson_summary
topic_status: completed
awaiting: student_confirmation
next_lesson_min_offset_hours: 3
"""

MALFORMED_RESPONSE = "Просто обычный текст без меток."

MARKDOWN_SPEECH_RESPONSE = """SPEECH: Разобрали сложение дробей.

**Вычитание дробей**

Теперь поговорим про `вычитание`. Смотри на доску.

---

# Итог

Молодец!
BOARD: none
STATE:
stage: explanation
topic_status: in_progress
awaiting: none
next_lesson_min_offset_hours: 3
"""


def test_parses_speech_board_state():
    parsed = parse_lesson_turn(SAMPLE_RESPONSE)

    assert parsed.speech == "Привет, Аня! Сегодня разберём обыкновенные дроби."
    assert parsed.board_type == "text"
    assert parsed.board_content == "Тема: Обыкновенные дроби"
    assert parsed.stage == "explanation"
    assert parsed.topic_status == "in_progress"
    assert parsed.awaiting == "none"
    assert parsed.next_lesson_min_offset_hours == 3


def test_board_none_parses_to_empty():
    parsed = parse_lesson_turn(NO_BOARD_RESPONSE)

    assert parsed.board_type is None
    assert parsed.board_content is None
    assert parsed.stage == "lesson_summary"
    assert parsed.topic_status == "completed"
    assert parsed.awaiting == "student_confirmation"


def test_malformed_response_falls_back_to_raw_speech():
    parsed = parse_lesson_turn(MALFORMED_RESPONSE)

    assert parsed.speech == MALFORMED_RESPONSE
    assert parsed.board_type is None
    assert parsed.stage is None


def test_speech_strips_markdown_so_tts_does_not_read_it_aloud():
    parsed = parse_lesson_turn(MARKDOWN_SPEECH_RESPONSE)

    assert "*" not in parsed.speech
    assert "#" not in parsed.speech
    assert "`" not in parsed.speech
    assert "---" not in parsed.speech
    assert parsed.speech == (
        "Разобрали сложение дробей.\n\n"
        "Вычитание дробей\n\n"
        "Теперь поговорим про вычитание. Смотри на доску.\n\n"
        "Итог\n\n"
        "Молодец!"
    )
