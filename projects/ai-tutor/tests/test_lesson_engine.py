from datetime import datetime, timedelta

import pytest

from app import db
from app.lesson_engine import (
    SchedulingError,
    handle_student_photo,
    next_topic_for_user,
    schedule_next_lesson,
    start_program_lesson,
)
from app.models import Task, Topic, User, UserProgress

KICKOFF_REPLY = """SPEECH: Привет! Сегодня разберём тему.
BOARD:
type: text
content: Тема 1
STATE:
stage: explanation
topic_status: in_progress
awaiting: none
next_lesson_min_offset_hours: 3
"""

TASK_GIVEN_REPLY = """SPEECH: Вот первое задание.
BOARD:
type: text
content: Реши пример.
STATE:
stage: task_given
topic_status: in_progress
awaiting: student_photo
next_lesson_min_offset_hours: 3
"""

TASK_CORRECT_REPLY = """SPEECH: Отлично, всё верно!
BOARD: none
STATE:
stage: task_correct
topic_status: completed
awaiting: student_confirmation
next_lesson_min_offset_hours: 3
"""


def _fake_send(responses):
    it = iter(responses)

    def _send(system_prompt, history, user_content):
        return next(it)

    return _send


def test_next_topic_for_user_returns_first_incomplete(app, user):
    with app.app_context():
        u = db.session.get(User, user)
        topic = next_topic_for_user(u)
        assert topic.order == 1


def test_next_topic_skips_completed(app, user):
    with app.app_context():
        u = db.session.get(User, user)
        first_topic = Topic.query.filter_by(order=1).first()
        db.session.add(
            UserProgress(user_id=u.id, topic_id=first_topic.id, status=UserProgress.STATUS_COMPLETED)
        )
        db.session.commit()

        topic = next_topic_for_user(u)
        assert topic.order == 2


def test_start_program_lesson_creates_task_and_marks_progress(app, user, monkeypatch):
    with app.app_context():
        u = db.session.get(User, user)
        monkeypatch.setattr(
            "app.lesson_engine.send_lesson_turn",
            _fake_send([KICKOFF_REPLY, TASK_GIVEN_REPLY]),
        )

        lesson = start_program_lesson(u)
        assert lesson.stage == "explanation"

        from app.lesson_engine import handle_student_text

        handle_student_text(lesson, u, "Понятно, что дальше?")
        assert lesson.stage == "task_given"
        assert len(lesson.tasks) == 1
        assert lesson.tasks[0].status == Task.STATUS_PENDING


def test_photo_submission_marks_task_correct_and_completes_topic(app, user, monkeypatch):
    with app.app_context():
        u = db.session.get(User, user)
        monkeypatch.setattr(
            "app.lesson_engine.send_lesson_turn",
            _fake_send([KICKOFF_REPLY, TASK_GIVEN_REPLY, TASK_CORRECT_REPLY]),
        )

        lesson = start_program_lesson(u)
        from app.lesson_engine import handle_student_text

        handle_student_text(lesson, u, "Понятно")

        handle_student_photo(lesson, u, b"fake-image-bytes", "solution.jpg", "image/jpeg")

        assert lesson.tasks[0].status == Task.STATUS_CORRECT
        assert lesson.tasks[0].submissions[0].correct is True

        progress = UserProgress.query.filter_by(user_id=u.id, topic_id=lesson.topic_id).first()
        assert progress.status == UserProgress.STATUS_COMPLETED


def test_schedule_next_lesson_rejects_too_soon(app, user, monkeypatch):
    with app.app_context():
        u = db.session.get(User, user)
        monkeypatch.setattr("app.lesson_engine.send_lesson_turn", _fake_send([KICKOFF_REPLY]))
        lesson = start_program_lesson(u)

        with pytest.raises(SchedulingError):
            schedule_next_lesson(u, lesson, datetime.utcnow() + timedelta(hours=1))


def test_schedule_next_lesson_accepts_valid_time(app, user, monkeypatch):
    with app.app_context():
        u = db.session.get(User, user)
        monkeypatch.setattr("app.lesson_engine.send_lesson_turn", _fake_send([KICKOFF_REPLY]))
        lesson = start_program_lesson(u)

        scheduled_at = datetime.utcnow() + timedelta(hours=4)
        session = schedule_next_lesson(u, lesson, scheduled_at)

        assert session.scheduled_at == scheduled_at
        assert lesson.status == "completed"
