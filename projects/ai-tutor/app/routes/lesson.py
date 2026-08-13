"""Занятие: чат с ИИ-репетитором, доска, загрузка фото решений, назначение
следующего занятия (разделы 4.2/4.3/4.4 ТЗ)."""
from datetime import datetime, timedelta

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.ai_client import AIClientError
from app.lesson_engine import (
    SchedulingError,
    handle_student_photo,
    handle_student_text,
    schedule_next_lesson,
    start_free_lesson,
    start_program_lesson,
)
from app.models import Lesson
from app.photos import MAX_PHOTO_SIZE

bp = Blueprint("lesson", __name__)


def _owned_lesson_or_404(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)
    if lesson.user_id != current_user.id:
        abort(404)
    return lesson


@bp.route("/start", methods=["POST"])
@login_required
def start():
    try:
        lesson = start_program_lesson(current_user)
    except AIClientError as exc:
        flash(str(exc), "error")
        return redirect(url_for("main.dashboard"))

    if lesson is None:
        flash("Вся программа по этому предмету и классу уже пройдена. Попробуйте свободный режим.", "info")
        return redirect(url_for("main.dashboard"))
    return redirect(url_for("lesson.chat", lesson_id=lesson.id))


@bp.route("/free", methods=["GET", "POST"])
@login_required
def free():
    if request.method == "POST":
        topic_text = (request.form.get("topic_text") or "").strip()
        if not topic_text:
            flash("Опишите тему, которая непонятна.", "error")
            return render_template("lesson/free.html")

        try:
            lesson = start_free_lesson(current_user, topic_text)
        except AIClientError as exc:
            flash(str(exc), "error")
            return render_template("lesson/free.html")

        return redirect(url_for("lesson.chat", lesson_id=lesson.id))

    return render_template("lesson/free.html")


@bp.route("/<int:lesson_id>")
@login_required
def chat(lesson_id):
    lesson = _owned_lesson_or_404(lesson_id)
    board_message = next(
        (m for m in reversed(lesson.messages) if m.sender == "tutor" and m.board_content), None
    )
    visible_messages = [m for m in lesson.messages if m.speech != "Начни занятие."]
    latest_speech = (
        visible_messages[-1].speech
        if visible_messages and visible_messages[-1].sender == "tutor"
        else None
    )
    min_offset_hours = current_app.config["NEXT_LESSON_MIN_OFFSET_HOURS"]
    min_datetime = (datetime.utcnow() + timedelta(hours=min_offset_hours)).strftime("%Y-%m-%dT%H:%M")
    return render_template(
        "lesson/chat.html",
        lesson=lesson,
        messages=visible_messages,
        board_message=board_message,
        latest_speech=latest_speech,
        min_offset_hours=min_offset_hours,
        min_datetime=min_datetime,
    )


@bp.route("/<int:lesson_id>/message", methods=["POST"])
@login_required
def send_message(lesson_id):
    lesson = _owned_lesson_or_404(lesson_id)
    if lesson.status != Lesson.STATUS_ACTIVE:
        flash("Это занятие уже завершено.", "info")
        return redirect(url_for("lesson.chat", lesson_id=lesson.id))

    text = (request.form.get("text") or "").strip()
    if not text:
        flash("Введите сообщение.", "error")
        return redirect(url_for("lesson.chat", lesson_id=lesson.id))

    idle_seconds = request.form.get("idle_seconds", type=int)

    try:
        handle_student_text(lesson, current_user, text, idle_seconds=idle_seconds)
    except AIClientError as exc:
        flash(str(exc), "error")
    return redirect(url_for("lesson.chat", lesson_id=lesson.id))


@bp.route("/<int:lesson_id>/photo", methods=["POST"])
@login_required
def send_photo(lesson_id):
    lesson = _owned_lesson_or_404(lesson_id)
    if lesson.status != Lesson.STATUS_ACTIVE:
        flash("Это занятие уже завершено.", "info")
        return redirect(url_for("lesson.chat", lesson_id=lesson.id))

    file = request.files.get("photo")
    if file is None or not file.filename:
        flash("Прикрепите фото решения.", "error")
        return redirect(url_for("lesson.chat", lesson_id=lesson.id))
    if not (file.mimetype or "").startswith("image/"):
        flash("Файл должен быть изображением.", "error")
        return redirect(url_for("lesson.chat", lesson_id=lesson.id))

    data = file.read()
    if len(data) > MAX_PHOTO_SIZE:
        flash("Фото слишком большое (максимум 10 МБ).", "error")
        return redirect(url_for("lesson.chat", lesson_id=lesson.id))

    try:
        handle_student_photo(lesson, current_user, data, file.filename, file.mimetype)
    except AIClientError as exc:
        flash(str(exc), "error")
    return redirect(url_for("lesson.chat", lesson_id=lesson.id))


@bp.route("/<int:lesson_id>/schedule", methods=["POST"])
@login_required
def schedule(lesson_id):
    lesson = _owned_lesson_or_404(lesson_id)

    raw_value = request.form.get("scheduled_at") or ""
    try:
        scheduled_at = datetime.strptime(raw_value, "%Y-%m-%dT%H:%M")
    except ValueError:
        flash("Укажите корректные дату и время.", "error")
        return redirect(url_for("lesson.chat", lesson_id=lesson.id))

    try:
        schedule_next_lesson(current_user, lesson, scheduled_at)
    except SchedulingError as exc:
        flash(str(exc), "error")
        return redirect(url_for("lesson.chat", lesson_id=lesson.id))

    flash("Следующее занятие запланировано!", "success")
    return redirect(url_for("main.dashboard"))
