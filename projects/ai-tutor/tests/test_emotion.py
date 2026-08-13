from app.emotion import infer_emotion_state
from app.models import Task


class FakeTask:
    def __init__(self, status):
        self.status = status


class FakeLesson:
    def __init__(self, tasks):
        self.tasks = tasks


def test_two_consecutive_incorrect_is_frustrated():
    lesson = FakeLesson([FakeTask(Task.STATUS_INCORRECT), FakeTask(Task.STATUS_INCORRECT)])
    assert infer_emotion_state(lesson) == "frustrated"


def test_single_incorrect_does_not_trigger_frustrated():
    lesson = FakeLesson([FakeTask(Task.STATUS_CORRECT), FakeTask(Task.STATUS_INCORRECT)])
    assert infer_emotion_state(lesson) != "frustrated"


def test_confused_phrase_detected():
    lesson = FakeLesson([])
    assert infer_emotion_state(lesson, message_text="Извините, я не понял объяснение") == "confused"


def test_long_idle_is_tired():
    lesson = FakeLesson([])
    assert infer_emotion_state(lesson, idle_seconds=180) == "tired"


def test_medium_idle_is_bored():
    lesson = FakeLesson([])
    assert infer_emotion_state(lesson, idle_seconds=60) == "bored"


def test_correct_last_task_is_engaged():
    lesson = FakeLesson([FakeTask(Task.STATUS_CORRECT)])
    assert infer_emotion_state(lesson) == "engaged"


def test_no_signal_returns_none():
    lesson = FakeLesson([])
    assert infer_emotion_state(lesson) is None
