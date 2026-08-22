"""Административная панель: единственный администратор входит по общему
паролю (сессия, без роли в таблице users — тот же паттерн, что в
istok/ai-tutor/b2b-platform). Здесь же — предохранители от разорения на
API: блокировка пользователей (по одному или все сразу), общий рубильник
всей программы и управление лимитами сообщений."""
import hmac
from functools import wraps

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for

from app import db
from app.models import SupportMessage, User, get_settings

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
        return redirect(url_for("admin.dashboard"))
    return redirect(url_for("admin.login"))


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        password = request.form.get("password", "")
        expected = current_app.config["ADMIN_PASSWORD"]
        if hmac.compare_digest(password, expected):
            session["is_admin"] = True
            flash("Вы вошли в панель управления.", "success")
            return redirect(request.args.get("next") or url_for("admin.dashboard"))
        flash("Неверный пароль.", "error")
    return render_template("admin/login.html")


@bp.route("/logout")
def logout():
    session.pop("is_admin", None)
    flash("Вы вышли из панели управления.", "info")
    return redirect(url_for("admin.login"))


@bp.route("/dashboard")
@login_required
def dashboard():
    settings = get_settings()
    stats = {
        "registered": User.query.count(),
        "confirmed": User.query.filter_by(email_confirmed=True).count(),
        "blocked": User.query.filter_by(is_blocked=True).count(),
        "paid": User.query.filter_by(is_paid=True).count(),
        "unread_support": SupportMessage.query.filter_by(
            sender=SupportMessage.SENDER_USER, read_by_admin=False
        ).count(),
    }
    return render_template("admin/dashboard.html", settings=settings, stats=stats)


# --- Пользователи ---

@bp.route("/users")
@login_required
def users():
    rows = User.query.order_by(User.created_at.desc()).all()
    settings = get_settings()
    return render_template("admin/users.html", users=rows, settings=settings)


@bp.route("/users/<int:user_id>/block", methods=["POST"])
@login_required
def block_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_blocked = not user.is_blocked
    if user.is_blocked:
        user.blocked_reason = (request.form.get("reason") or "").strip() or None
    else:
        user.blocked_reason = None
    db.session.commit()
    flash(f'{"Заблокирован" if user.is_blocked else "Разблокирован"}: {user.email}.', "info")
    return redirect(url_for("admin.users"))


@bp.route("/users/block-all", methods=["POST"])
@login_required
def block_all():
    count = User.query.filter_by(is_blocked=False).update({"is_blocked": True})
    db.session.commit()
    flash(f"Заблокировано пользователей: {count}.", "info")
    return redirect(url_for("admin.users"))


@bp.route("/users/unblock-all", methods=["POST"])
@login_required
def unblock_all():
    count = User.query.filter_by(is_blocked=True).update({"is_blocked": False, "blocked_reason": None})
    db.session.commit()
    flash(f"Разблокировано пользователей: {count}.", "info")
    return redirect(url_for("admin.users"))


@bp.route("/users/<int:user_id>/paid", methods=["POST"])
@login_required
def toggle_paid(user_id):
    user = User.query.get_or_404(user_id)
    user.is_paid = not user.is_paid
    db.session.commit()
    flash(f'Статус оплаты для {user.email}: {"оплачено" if user.is_paid else "не оплачено"}.', "info")
    return redirect(url_for("admin.users"))


@bp.route("/users/<int:user_id>/limit", methods=["POST"])
@login_required
def set_limit(user_id):
    user = User.query.get_or_404(user_id)
    raw_value = (request.form.get("message_limit") or "").strip()

    if not raw_value:
        user.message_limit = None
        flash(f"Индивидуальный лимит для {user.email} снят (используется общий).", "info")
    else:
        try:
            limit = int(raw_value)
        except ValueError:
            flash("Лимит должен быть целым числом.", "error")
            return redirect(url_for("admin.users"))
        if limit < 0:
            flash("Лимит не может быть отрицательным.", "error")
            return redirect(url_for("admin.users"))
        user.message_limit = limit
        flash(f"Лимит для {user.email} установлен: {limit}.", "success")

    db.session.commit()
    return redirect(url_for("admin.users"))


@bp.route("/users/<int:user_id>/reset-usage", methods=["POST"])
@login_required
def reset_usage(user_id):
    user = User.query.get_or_404(user_id)
    user.messages_used = 0
    db.session.commit()
    flash(f"Счётчик сообщений для {user.email} сброшен.", "info")
    return redirect(url_for("admin.users"))


@bp.route("/users/<int:user_id>/delete", methods=["POST"])
@login_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    email = user.email
    db.session.delete(user)
    db.session.commit()
    flash(f'Пользователь "{email}" и все его данные удалены.', "info")
    return redirect(url_for("admin.users"))


# --- Общие настройки: рубильник всей программы и лимиты ---

@bp.route("/settings/kill-switch", methods=["POST"])
@login_required
def toggle_kill_switch():
    settings = get_settings()
    settings.app_enabled = not settings.app_enabled
    message = (request.form.get("disabled_message") or "").strip()
    if message:
        settings.disabled_message = message
    db.session.commit()
    flash(
        "Приложение включено для всех." if settings.app_enabled else "Приложение полностью отключено для всех пользователей.",
        "info",
    )
    return redirect(url_for("admin.dashboard"))


@bp.route("/settings/limits", methods=["POST"])
@login_required
def update_limits():
    settings = get_settings()
    settings.limits_enabled = request.form.get("limits_enabled") == "on"

    raw_default = (request.form.get("default_message_limit") or "").strip()
    if raw_default:
        try:
            value = int(raw_default)
            if value >= 0:
                settings.default_message_limit = value
        except ValueError:
            flash("Общий лимит по умолчанию должен быть целым числом.", "error")
            return redirect(url_for("admin.dashboard"))

    db.session.commit()
    flash(
        "Лимиты сообщений включены." if settings.limits_enabled else "Все лимиты сообщений отключены — расходы на API теперь ничем не ограничены.",
        "info",
    )
    return redirect(url_for("admin.dashboard"))


# --- Поддержка ---

@bp.route("/support")
@login_required
def support_list():
    users_with_threads = (
        db.session.query(User)
        .join(SupportMessage, SupportMessage.user_id == User.id)
        .distinct()
        .all()
    )
    rows = []
    for user in users_with_threads:
        unread = SupportMessage.query.filter_by(
            user_id=user.id, sender=SupportMessage.SENDER_USER, read_by_admin=False
        ).count()
        last = (
            SupportMessage.query.filter_by(user_id=user.id)
            .order_by(SupportMessage.created_at.desc())
            .first()
        )
        rows.append({"user": user, "unread": unread, "last": last})
    rows.sort(key=lambda r: r["last"].created_at if r["last"] else "", reverse=True)
    return render_template("admin/support.html", rows=rows)


@bp.route("/support/<int:user_id>", methods=["GET", "POST"])
@login_required
def support_thread(user_id):
    user = User.query.get_or_404(user_id)

    if request.method == "POST":
        body = (request.form.get("body") or "").strip()
        if body:
            db.session.add(SupportMessage(
                user_id=user.id, sender=SupportMessage.SENDER_ADMIN, body=body,
            ))
            db.session.commit()
            flash("Ответ отправлен.", "success")
        return redirect(url_for("admin.support_thread", user_id=user.id))

    messages = (
        SupportMessage.query.filter_by(user_id=user.id).order_by(SupportMessage.created_at).all()
    )
    for m in messages:
        if m.sender == SupportMessage.SENDER_USER and not m.read_by_admin:
            m.read_by_admin = True
    db.session.commit()

    return render_template("admin/support_thread.html", support_user=user, messages=messages)
