"""Учебный движок (Lesson Engine) — раздел 5 ТЗ: оркестрация цикла занятия
(объяснение -> проверка понимания -> задания -> проверка решений -> итог ->
назначение следующего занятия). Обращается к ИИ-API с системным промптом
репетитора и парсит ответ по трём блокам SPEECH/BOARD/STATE (раздел 7 ТЗ).

Назначение следующего занятия в MVP — простое поле даты/времени с проверкой
интервала (раздел 9.1 ТЗ), а не разбор свободного текста моделью: как
только занятие доходит до этапа scheduling_next, интерфейс показывает форму
выбора времени (см. app/routes/lesson.py), и её отправка, а не реплика в
чате, закрывает занятие."""
from datetime import datetime, timedelta

from flask import current_app

from app import db
from app.ai_client import build_photo_content, send_lesson_turn
from app.lesson_parser import parse_lesson_turn
from app.models import Lesson, LessonMessage, Task, TaskSubmission, UserProgress
from app.photos import upload_photo_bytes
from app.prompts import build_lesson_system_prompt

KICKOFF_MESSAGE = "Начни занятие."


class SchedulingError(ValueError):
    """Выбранное время следующего занятия не проходит проверку интервала."""


def next_topic_for_user(user):
    """Первая ещё не пройденная тема программы ученика (раздел 4.2 ТЗ), или
    None, если программа не выбрана или уже полностью пройдена."""
    program = user.program
    if program is None:
        return None
    completed_ids = {
        row.topic_id
        for row in UserProgress.query.filter_by(
            user_id=user.id, status=UserProgress.STATUS_COMPLETED
        )
    }
    for topic in program.topics:
        if topic.id not in completed_ids:
            return topic
    return None


def completed_topic_titles(user):
    rows = UserProgress.query.filter_by(
        user_id=user.id, status=UserProgress.STATUS_COMPLETED
    ).all()
    return [row.topic.title for row in rows]


def active_lesson_for_user(user):
    return (
        Lesson.query.filter_by(user_id=user.id, status=Lesson.STATUS_ACTIVE)
        .order_by(Lesson.started_at.desc())
        .first()
    )


def start_program_lesson(user):
    """Создаёт плановое занятие по следующей неизученной теме программы."""
    topic = next_topic_for_user(user)
    if topic is None:
        return None

    lesson = Lesson(
        user_id=user.id,
        topic_id=topic.id,
        mode=Lesson.MODE_PROGRAM,
        tasks_required=current_app.config["MIN_TASKS_PER_LESSON"],
    )
    db.session.add(lesson)
    db.session.flush()

    progress = UserProgress.query.filter_by(user_id=user.id, topic_id=topic.id).first()
    if progress is None:
        progress = UserProgress(
            user_id=user.id, topic_id=topic.id, status=UserProgress.STATUS_IN_PROGRESS
        )
        db.session.add(progress)
    else:
        progress.status = UserProgress.STATUS_IN_PROGRESS
    db.session.commit()

    _apply_ai_turn(lesson, user, user_content=KICKOFF_MESSAGE, student_message_speech=KICKOFF_MESSAGE)
    return lesson


def start_free_lesson(user, free_topic_text):
    """Создаёт занятие в свободном режиме по теме, введённой учеником (раздел 4.3 ТЗ)."""
    lesson = Lesson(
        user_id=user.id,
        mode=Lesson.MODE_FREE,
        free_topic_text=free_topic_text,
        tasks_required=current_app.config["MIN_TASKS_PER_LESSON"],
    )
    db.session.add(lesson)
    db.session.commit()

    _apply_ai_turn(lesson, user, user_content=KICKOFF_MESSAGE, student_message_speech=KICKOFF_MESSAGE)
    return lesson


def handle_student_text(lesson, user, text):
    """Ученик прислал текстовое сообщение (ответ, вопрос по ходу, "понятно" и т.п.)."""
    return _apply_ai_turn(lesson, user, user_content=text, student_message_speech=text)


def handle_student_photo(lesson, user, data, filename, mimetype):
    """Ученик прислал фото решения задания (раздел 4.2/7 ТЗ)."""
    photo_url = upload_photo_bytes(data, filename, mimetype)
    caption = "Вот моё решение."
    content = build_photo_content(caption, data, mimetype)
    return _apply_ai_turn(
        lesson, user, user_content=content, student_message_speech=caption, student_photo_url=photo_url
    )


def schedule_next_lesson(user, lesson, scheduled_at):
    """Фиксирует выбранное учеником время следующего занятия и закрывает
    текущее занятие. scheduled_at — naive datetime в UTC."""
    min_offset_hours = current_app.config["NEXT_LESSON_MIN_OFFSET_HOURS"]
    earliest = datetime.utcnow() + timedelta(hours=min_offset_hours)
    if scheduled_at < earliest:
        raise SchedulingError(
            f"Следующее занятие можно назначить не раньше чем через {min_offset_hours} ч."
        )

    from app.models import ScheduledSession

    session = ScheduledSession(user_id=user.id, lesson_id=lesson.id, scheduled_at=scheduled_at)
    db.session.add(session)

    lesson.status = Lesson.STATUS_COMPLETED
    lesson.ended_at = datetime.utcnow()

    db.session.commit()
    return session


def _history_messages(lesson):
    """Собирает историю диалога занятия в формате Anthropic Messages API
    (раздел 7 ТЗ: "передавать историю диалога занятия, не начинать контекст
    с нуля"). Фото прошлых сообщений не пересылаются повторно — вместо
    байтов изображения в истории остаётся текстовая пометка, ответ модели
    на это сообщение (уже проанализировавший фото) сохранён следующим
    ходом ассистента и несёт нужный контекст."""
    messages = []
    for msg in lesson.messages:
        if msg.sender == LessonMessage.SENDER_STUDENT:
            text = msg.speech or ""
            if msg.photo_url is not None:
                text = f"[Ученик прислал фото решения] {text}".strip()
            messages.append({"role": "user", "content": text})
        else:
            messages.append({"role": "assistant", "content": msg.raw_response or msg.speech or ""})
    return messages


def _apply_ai_turn(lesson, user, user_content, student_message_speech=None, student_photo_url=None):
    history = _history_messages(lesson)

    system_prompt = build_lesson_system_prompt(
        avatar_name=current_app.config["DEFAULT_AVATAR_NAME"],
        student_name=user.name,
        student_grade=user.grade.name if user.grade else "не указан",
        mode=lesson.mode,
        subject_name=lesson.subject_name,
        topic_title=lesson.topic.title if lesson.topic else None,
        topic_description=lesson.topic.description if lesson.topic else None,
        free_topic_text=lesson.free_topic_text,
        completed_topics=completed_topic_titles(user),
    )

    raw_response = send_lesson_turn(system_prompt, history, user_content)
    parsed = parse_lesson_turn(raw_response)

    db.session.add(
        LessonMessage(
            lesson_id=lesson.id,
            sender=LessonMessage.SENDER_STUDENT,
            speech=student_message_speech,
            photo_url=student_photo_url,
        )
    )
    db.session.add(
        LessonMessage(
            lesson_id=lesson.id,
            sender=LessonMessage.SENDER_TUTOR,
            speech=parsed.speech,
            board_type=parsed.board_type,
            board_content=parsed.board_content,
            raw_response=raw_response,
        )
    )

    lesson.stage = parsed.stage
    lesson.awaiting = parsed.awaiting

    _apply_state_side_effects(lesson, user, parsed, student_photo_url)

    db.session.commit()
    return parsed


def _apply_state_side_effects(lesson, user, parsed, student_photo_url):
    if parsed.stage == "task_given":
        db.session.add(
            Task(
                lesson_id=lesson.id,
                order=len(lesson.tasks) + 1,
                text=parsed.board_content or parsed.speech,
                status=Task.STATUS_PENDING,
            )
        )
        db.session.flush()

    if student_photo_url is not None or parsed.stage in ("task_correct", "task_incorrect"):
        open_task = next((t for t in reversed(lesson.tasks) if t.status == Task.STATUS_PENDING), None)
        if open_task is not None:
            correct = True if parsed.stage == "task_correct" else (
                False if parsed.stage == "task_incorrect" else None
            )
            db.session.add(
                TaskSubmission(
                    task_id=open_task.id,
                    photo_url=student_photo_url,
                    correct=correct,
                    feedback=parsed.speech,
                )
            )
            if correct is True:
                open_task.status = Task.STATUS_CORRECT
            elif correct is False:
                open_task.status = Task.STATUS_INCORRECT

    if parsed.topic_status == "completed" and lesson.mode == Lesson.MODE_PROGRAM and lesson.topic_id:
        progress = UserProgress.query.filter_by(user_id=user.id, topic_id=lesson.topic_id).first()
        if progress is not None:
            progress.status = UserProgress.STATUS_COMPLETED
            progress.completed_at = datetime.utcnow()
