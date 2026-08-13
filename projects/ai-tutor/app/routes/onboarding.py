"""Первый вход: выбор предмета/класса и отметка уже известных тем (раздел 4.1 ТЗ)."""
from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.models import Grade, Program, Subject, UserProgress

bp = Blueprint("onboarding", __name__)


@bp.route("/subject", methods=["GET", "POST"])
@login_required
def choose_subject():
    # MVP: программа — фиксированный список в БД (раздел 9.1 ТЗ), поэтому
    # ученику предлагаются только пары предмет+класс, для которых программа
    # уже засеяна (см. seed.py), а не любые комбинации справочников.
    programs = (
        Program.query.join(Subject).join(Grade).order_by(Grade.order, Subject.name).all()
    )

    if request.method == "POST":
        program_id = request.form.get("program_id", type=int)
        program = next((p for p in programs if p.id == program_id), None)
        if program is None:
            flash("Выберите предмет и класс из списка.", "error")
            return render_template("onboarding/subject.html", programs=programs)

        current_user.subject_id = program.subject_id
        current_user.grade_id = program.grade_id
        db.session.commit()
        return redirect(url_for("onboarding.known_topics"))

    return render_template("onboarding/subject.html", programs=programs)


@bp.route("/known-topics", methods=["GET", "POST"])
@login_required
def known_topics():
    program = current_user.program
    if program is None:
        return redirect(url_for("onboarding.choose_subject"))

    if request.method == "POST":
        known_ids = {int(v) for v in request.form.getlist("known_topic_id")}
        existing = {
            row.topic_id: row
            for row in UserProgress.query.filter_by(user_id=current_user.id).all()
        }
        for topic in program.topics:
            if topic.id not in known_ids:
                continue
            row = existing.get(topic.id)
            if row is None:
                row = UserProgress(user_id=current_user.id, topic_id=topic.id)
                db.session.add(row)
            row.status = UserProgress.STATUS_COMPLETED
            row.completed_at = datetime.utcnow()
        db.session.commit()
        flash("Программа настроена — можно начинать первое занятие.", "success")
        return redirect(url_for("main.dashboard"))

    return render_template("onboarding/known_topics.html", program=program)
