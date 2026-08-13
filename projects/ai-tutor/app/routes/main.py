"""Стартовая страница и личный кабинет ученика (раздел 5 ТЗ, модуль «Личный кабинет / профиль»)."""
from flask import Blueprint, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.lesson_engine import active_lesson_for_user, next_topic_for_user
from app.models import ScheduledSession, UserProgress

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    if not current_user.is_authenticated:
        return render_template("main/landing.html")
    if current_user.avatar_key is None:
        return redirect(url_for("onboarding.choose_avatar"))
    if current_user.subject_id is None or current_user.grade_id is None:
        return redirect(url_for("onboarding.choose_subject"))
    return redirect(url_for("main.dashboard"))


@bp.route("/dashboard")
@login_required
def dashboard():
    if current_user.avatar_key is None:
        return redirect(url_for("onboarding.choose_avatar"))
    if current_user.subject_id is None or current_user.grade_id is None:
        return redirect(url_for("onboarding.choose_subject"))

    program = current_user.program
    progress_by_topic = {
        row.topic_id: row
        for row in UserProgress.query.filter_by(user_id=current_user.id).all()
    }
    topics_progress = [
        (topic, progress_by_topic.get(topic.id))
        for topic in (program.topics if program else [])
    ]

    completed_count = sum(1 for _, progress in topics_progress if progress and progress.status == "completed")

    active_lesson = active_lesson_for_user(current_user)
    next_topic = next_topic_for_user(current_user) if active_lesson is None else None
    next_session = (
        ScheduledSession.query.filter_by(
            user_id=current_user.id, status=ScheduledSession.STATUS_SCHEDULED
        )
        .order_by(ScheduledSession.scheduled_at.desc())
        .first()
    )

    return render_template(
        "main/dashboard.html",
        program=program,
        topics_progress=topics_progress,
        completed_count=completed_count,
        active_lesson=active_lesson,
        next_topic=next_topic,
        next_session=next_session,
    )
