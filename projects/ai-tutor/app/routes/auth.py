"""Регистрация, вход и подтверждение email ученика (раздел 3 ТЗ, роль «Ученик»)."""
import re
from datetime import datetime

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash

from app import db
from app.email import send_email
from app.models import User

bp = Blueprint("auth", __name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
CONFIRM_SALT = "email-confirm"


def _serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"])


def confirm_url_for(user):
    token = _serializer().dumps(user.email, salt=CONFIRM_SALT)
    return url_for("auth.confirm_email", token=token, _external=True)


def _send_confirmation_email(user):
    confirm_url = confirm_url_for(user)
    body = (
        f"Здравствуйте, {user.name}!\n\n"
        f"Подтвердите регистрацию в модуле «ИИ-репетитор», перейдя по ссылке:\n"
        f"{confirm_url}\n\n"
        f"Ссылка действительна {current_app.config['CONFIRM_TOKEN_MAX_AGE'] // 3600} часов. "
        f"Если вы не регистрировались — просто проигнорируйте это письмо."
    )
    sent = send_email(user.email, "Подтверждение регистрации — ИИ-репетитор", body)
    return sent, confirm_url


def _flash_confirmation_result(sent, confirm_url):
    """Сообщение после (пере)отправки письма подтверждения.

    Важно: ссылку подтверждения показываем прямо пользователю ТОЛЬКО в
    режиме разработки (DEBUG) — это исключительно удобство локального
    тестирования без настоящего email-провайдера. В проде, если отправка
    не удалась (Resend не настроен/отклонил/упал), ссылку никому не
    показываем — иначе подтверждение email превращается в кнопку "поверь
    мне на слово", а не в реальную проверку, что ученик владеет этим
    почтовым ящиком (см. app/__init__.py: доступ к сайту гейтится именно
    по email_confirmed)."""
    if sent:
        flash("Письмо со ссылкой подтверждения отправлено на ваш email.", "success")
    elif current_app.debug:
        flash(f"[режим разработки] Почта не отправляется, вот ссылка: {confirm_url}", "info")
    else:
        flash(
            "Не удалось отправить письмо с подтверждением. Попробуйте запросить его ещё "
            "раз через пару минут или обратитесь в поддержку.",
            "error",
        )


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        password2 = request.form.get("password2") or ""

        if not name:
            flash("Введите имя ученика.", "error")
            return render_template("auth/register.html", name=name, email=email)
        if not EMAIL_RE.match(email):
            flash("Введите корректный email.", "error")
            return render_template("auth/register.html", name=name, email=email)
        if len(password) < 8:
            flash("Пароль должен быть не короче 8 символов.", "error")
            return render_template("auth/register.html", name=name, email=email)
        if password != password2:
            flash("Пароли не совпадают.", "error")
            return render_template("auth/register.html", name=name, email=email)
        if User.query.filter_by(email=email).first() is not None:
            flash("Этот email уже зарегистрирован. Попробуйте войти.", "error")
            return render_template("auth/register.html", name=name, email=email)

        user = User(name=name, email=email, password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()

        login_user(user)

        sent, confirm_url = _send_confirmation_email(user)
        _flash_confirmation_result(sent, confirm_url)
        return redirect(url_for("auth.confirm_pending"))

    return render_template("auth/register.html", name="", email="")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        user = User.query.filter_by(email=email).first()
        if user is None or not check_password_hash(user.password_hash, password):
            flash("Неверный email или пароль.", "error")
            return render_template("auth/login.html", email=email)

        login_user(user)
        flash("Вы вошли в личный кабинет.", "success")
        return redirect(request.args.get("next") or url_for("main.dashboard"))

    return render_template("auth/login.html", email="")


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Вы вышли из аккаунта.", "info")
    return redirect(url_for("main.index"))


@bp.route("/confirm/<token>")
def confirm_email(token):
    try:
        email = _serializer().loads(
            token, salt=CONFIRM_SALT, max_age=current_app.config["CONFIRM_TOKEN_MAX_AGE"]
        )
    except SignatureExpired:
        flash("Ссылка подтверждения устарела. Запросите новую в личном кабинете.", "error")
        return redirect(url_for("main.index"))
    except BadSignature:
        flash("Ссылка подтверждения недействительна.", "error")
        return redirect(url_for("main.index"))

    user = User.query.filter_by(email=email).first()
    if user is None:
        flash("Пользователь не найден.", "error")
        return redirect(url_for("main.index"))

    if not user.email_confirmed:
        user.email_confirmed = True
        user.confirmed_at = datetime.utcnow()
        db.session.commit()

    flash("Email подтверждён, спасибо!", "success")
    return redirect(url_for("main.index"))


@bp.route("/resend-confirmation")
@login_required
def resend_confirmation():
    if current_user.email_confirmed:
        flash("Email уже подтверждён.", "info")
        return redirect(url_for("main.index"))

    sent, confirm_url = _send_confirmation_email(current_user)
    _flash_confirmation_result(sent, confirm_url)
    return redirect(url_for("auth.confirm_pending"))


@bp.route("/confirm-pending")
@login_required
def confirm_pending():
    """Страница-заглушка: пока email не подтверждён, остальной сайт
    недоступен (см. before_request-гейт в app/__init__.py) — сюда
    редиректит и после регистрации, и при попытке зайти куда-либо ещё."""
    if current_user.email_confirmed:
        return redirect(url_for("main.index"))
    return render_template("auth/confirm_pending.html")
