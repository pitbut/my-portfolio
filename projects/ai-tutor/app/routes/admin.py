"""Административная панель: управление предметами/классами/программами и
просмотр прогресса учеников (раздел 5 ТЗ, модуль «Административная панель»,
этап 9.3). Авторизация — общий пароль на сессию, без отдельной роли в
таблице users (тот же паттерн, что в istok/b2b-platform)."""
import hmac
from functools import wraps

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for

from app import db
from app.email import send_email
from app.models import Grade, Lesson, Program, ScheduledSession, Subject, Topic, User, UserProgress
from app.slugify import slugify

bp = Blueprint("admin", __name__, template_folder="../templates/admin")


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("admin.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


@bp.route("/")
def index():
    if session.get("is_admin"):
        return redirect(url_for("admin.programs"))
    return redirect(url_for("admin.login"))


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        password = request.form.get("password", "")
        expected = current_app.config["ADMIN_PASSWORD"]
        if hmac.compare_digest(password, expected):
            session["is_admin"] = True
            flash("Вы вошли в панель управления.", "success")
            return redirect(request.args.get("next") or url_for("admin.programs"))
        flash("Неверный пароль.", "error")
    return render_template("admin/login.html")


@bp.route("/logout")
def logout():
    session.pop("is_admin", None)
    flash("Вы вышли из панели управления.", "info")
    return redirect(url_for("admin.login"))


@bp.route("/programs", methods=["GET", "POST"])
@login_required
def programs():
    if request.method == "POST":
        form = request.form.get("form")

        if form == "new_subject":
            name = (request.form.get("subject_name") or "").strip()
            if name and Subject.query.filter_by(name=name).first() is None:
                db.session.add(Subject(slug=slugify(name, "subject"), name=name))
                db.session.commit()
                flash(f'Предмет "{name}" добавлен.', "success")

        elif form == "new_grade":
            name = (request.form.get("grade_name") or "").strip()
            order = request.form.get("grade_order", type=int) or 0
            if name and Grade.query.filter_by(name=name).first() is None:
                db.session.add(Grade(slug=slugify(name, "grade"), name=name, order=order))
                db.session.commit()
                flash(f'Класс/уровень "{name}" добавлен.', "success")

        elif form == "new_program":
            subject_id = request.form.get("subject_id", type=int)
            grade_id = request.form.get("grade_id", type=int)
            if subject_id and grade_id:
                existing = Program.query.filter_by(subject_id=subject_id, grade_id=grade_id).first()
                if existing is not None:
                    flash("Такая программа уже существует.", "error")
                    return redirect(url_for("admin.topics", program_id=existing.id))
                program = Program(subject_id=subject_id, grade_id=grade_id)
                db.session.add(program)
                db.session.commit()
                flash("Программа создана — добавьте темы.", "success")
                return redirect(url_for("admin.topics", program_id=program.id))

        return redirect(url_for("admin.programs"))

    return render_template(
        "admin/programs.html",
        subjects=Subject.query.order_by(Subject.name).all(),
        grades=Grade.query.order_by(Grade.order).all(),
        program_list=Program.query.join(Subject).join(Grade).order_by(Grade.order, Subject.name).all(),
    )


@bp.route("/programs/<int:program_id>/topics", methods=["GET", "POST"])
@login_required
def topics(program_id):
    program = Program.query.get_or_404(program_id)

    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        description = (request.form.get("description") or "").strip() or None
        order = request.form.get("order", type=int)
        if not title:
            flash("Введите название темы.", "error")
        else:
            if order is None:
                order = (max((t.order for t in program.topics), default=0)) + 1
            db.session.add(Topic(program_id=program.id, order=order, title=title, description=description))
            db.session.commit()
            flash(f'Тема "{title}" добавлена.', "success")
        return redirect(url_for("admin.topics", program_id=program.id))

    next_order = max((t.order for t in program.topics), default=0) + 1
    return render_template("admin/topics.html", program=program, next_order=next_order)


@bp.route("/topics/<int:topic_id>/delete", methods=["POST"])
@login_required
def delete_topic(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    program_id = topic.program_id
    db.session.delete(topic)
    db.session.commit()
    flash("Тема удалена.", "info")
    return redirect(url_for("admin.topics", program_id=program_id))


@bp.route("/students")
@login_required
def students():
    rows = []
    for user in User.query.order_by(User.created_at.desc()).all():
        program = user.program
        total = len(program.topics) if program else 0
        completed = (
            UserProgress.query.filter_by(user_id=user.id, status=UserProgress.STATUS_COMPLETED).count()
            if program
            else 0
        )
        next_session = (
            ScheduledSession.query.filter_by(user_id=user.id, status=ScheduledSession.STATUS_SCHEDULED)
            .order_by(ScheduledSession.scheduled_at.desc())
            .first()
        )
        rows.append(
            {
                "user": user,
                "program": program,
                "total": total,
                "completed": completed,
                "next_session": next_session,
            }
        )

    stats = {
        "registered": User.query.count(),
        "lessons_total": Lesson.query.count(),
        "lessons_active": Lesson.query.filter_by(status=Lesson.STATUS_ACTIVE).count(),
    }
    return render_template("admin/students.html", rows=rows, stats=stats)


@bp.route("/students/<int:user_id>")
@login_required
def student_detail(user_id):
    user = User.query.get_or_404(user_id)
    program = user.program
    total = len(program.topics) if program else 0
    completed = (
        UserProgress.query.filter_by(user_id=user.id, status=UserProgress.STATUS_COMPLETED).count()
        if program
        else 0
    )
    lessons = Lesson.query.filter_by(user_id=user.id).order_by(Lesson.started_at.desc()).all()
    sessions = (
        ScheduledSession.query.filter_by(user_id=user.id).order_by(ScheduledSession.scheduled_at.desc()).all()
    )
    return render_template(
        "admin/student_detail.html",
        student=user,
        program=program,
        total=total,
        completed=completed,
        lessons=lessons,
        sessions=sessions,
    )


@bp.route("/students/<int:user_id>/limit", methods=["POST"])
@login_required
def student_set_limit(user_id):
    user = User.query.get_or_404(user_id)
    raw_value = (request.form.get("token_limit") or "").strip()

    if not raw_value:
        user.token_limit = None
        flash("Лимит токенов снят.", "info")
    else:
        try:
            limit = int(raw_value)
        except ValueError:
            flash("Лимит должен быть целым числом.", "error")
            return redirect(url_for("admin.student_detail", user_id=user.id))
        if limit < 0:
            flash("Лимит не может быть отрицательным.", "error")
            return redirect(url_for("admin.student_detail", user_id=user.id))
        user.token_limit = limit
        flash(f"Лимит токенов установлен: {limit}.", "success")

    db.session.commit()
    return redirect(url_for("admin.student_detail", user_id=user.id))


@bp.route("/students/<int:user_id>/delete", methods=["POST"])
@login_required
def student_delete(user_id):
    user = User.query.get_or_404(user_id)

    # Удаляем зависимые записи явно (в модели нет ondelete=CASCADE на уровне
    # БД для user_id) — сначала занятия (у Lesson уже настроен ORM-каскад на
    # messages/tasks/submissions), затем прогресс и запланированные сессии.
    for lesson in Lesson.query.filter_by(user_id=user.id).all():
        db.session.delete(lesson)
    UserProgress.query.filter_by(user_id=user.id).delete()
    ScheduledSession.query.filter_by(user_id=user.id).delete()

    name = user.name
    db.session.delete(user)
    db.session.commit()
    flash(f'Ученик "{name}" и все его данные удалены.', "info")
    return redirect(url_for("admin.students"))


@bp.route("/students/<int:user_id>/email", methods=["POST"])
@login_required
def student_email(user_id):
    user = User.query.get_or_404(user_id)
    subject = (request.form.get("subject") or "").strip()
    body = (request.form.get("body") or "").strip()

    if not subject or not body:
        flash("Заполните тему и текст письма.", "error")
        return redirect(url_for("admin.student_detail", user_id=user.id))

    sent = send_email(user.email, subject, body)
    if sent:
        flash(f"Письмо отправлено на {user.email}.", "success")
    else:
        flash(
            "Не удалось отправить письмо (см. лог сервера — например, Resend не настроен "
            "или отклонил отправку). Текст письма записан в лог.",
            "error",
        )
    return redirect(url_for("admin.student_detail", user_id=user.id))
