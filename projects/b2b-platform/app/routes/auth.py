"""Модуль 1 — регистрация, вход (email и Google), подтверждение email, выбор роли."""
import re
from datetime import datetime

from authlib.common.security import generate_token
from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash

from app import db, get_google_client
from app.email import send_email
from app.i18n import SUPPORTED_LANGUAGES
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
        "Здравствуйте!\n\n"
        "Подтвердите регистрацию на B2B-платформе изготовителей и ремонтников оборудования, "
        f"перейдя по ссылке:\n{confirm_url}\n\n"
        f"Ссылка действительна {current_app.config['CONFIRM_TOKEN_MAX_AGE'] // 3600} часов. "
        "Если вы не регистрировались на сайте — просто проигнорируйте это письмо."
    )
    sent = send_email(user.email, "Подтверждение регистрации", body)
    return sent, confirm_url


def _post_login_redirect():
    next_url = request.args.get("next") or request.form.get("next")
    if current_user.role is None:
        return redirect(url_for("auth.choose_role", next=next_url) if next_url else url_for("auth.choose_role"))
    if next_url:
        return redirect(next_url)
    if current_user.role == "customer":
        return redirect(url_for("profile.customer_edit"))
    if current_user.role == "executor":
        return redirect(url_for("profile.executor_edit"))
    return redirect(url_for("main.index"))


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        password2 = request.form.get("password2") or ""
        role = request.form.get("role")
        language = request.form.get("language") or "ru"
        next_url = request.form.get("next") or ""

        form_ctx = {"email": email, "role": role, "language": language, "next_url": next_url}

        if not EMAIL_RE.match(email):
            flash("Введите корректный email.", "error")
            return render_template("auth/register.html", **form_ctx)
        if len(password) < 8:
            flash("Пароль должен быть не короче 8 символов.", "error")
            return render_template("auth/register.html", **form_ctx)
        if password != password2:
            flash("Пароли не совпадают.", "error")
            return render_template("auth/register.html", **form_ctx)
        if role not in ("customer", "executor"):
            flash("Выберите, вы заказчик или исполнитель.", "error")
            return render_template("auth/register.html", **form_ctx)
        if language not in SUPPORTED_LANGUAGES:
            language = "ru"
        if User.query.filter_by(email=email).first() is not None:
            flash("Этот email уже зарегистрирован. Попробуйте войти.", "error")
            return render_template("auth/register.html", **form_ctx)

        user = User(
            email=email,
            password_hash=generate_password_hash(password),
            role=role,
            preferred_language=language,
            last_login_at=datetime.utcnow(),
        )
        db.session.add(user)
        db.session.commit()

        login_user(user)
        session["lang"] = language

        sent, confirm_url = _send_confirmation_email(user)
        if sent:
            flash("Регистрация почти завершена — мы отправили письмо со ссылкой подтверждения на ваш email.", "success")
        else:
            flash(
                f"Регистрация завершена. Почтовый сервер ещё не настроен, поэтому подтвердите email по этой ссылке: {confirm_url}",
                "info",
            )

        if role == "customer":
            return redirect(url_for("profile.customer_edit", next=next_url) if next_url else url_for("profile.customer_edit"))
        return redirect(url_for("profile.executor_edit", next=next_url) if next_url else url_for("profile.executor_edit"))

    return render_template(
        "auth/register.html",
        email="",
        role=request.args.get("role", ""),
        language="ru",
        next_url=request.args.get("next", ""),
    )


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    next_url = request.args.get("next") or request.form.get("next") or ""

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        user = User.query.filter_by(email=email).first()
        if user is None or not user.password_hash or not check_password_hash(user.password_hash, password):
            flash("Неверный email или пароль.", "error")
            return render_template("auth/login.html", email=email, next_url=next_url)
        if user.is_blocked:
            flash("Аккаунт заблокирован. Обратитесь в поддержку.", "error")
            return render_template("auth/login.html", email=email, next_url=next_url)

        user.last_login_at = datetime.utcnow()
        db.session.commit()
        login_user(user)
        flash("Вы вошли на сайт.", "success")
        return _post_login_redirect()

    return render_template("auth/login.html", email="", next_url=next_url)


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Вы вышли из аккаунта.", "info")
    return redirect(url_for("main.index"))


@bp.route("/confirm/<token>")
def confirm_email(token):
    try:
        email = _serializer().loads(token, salt=CONFIRM_SALT, max_age=current_app.config["CONFIRM_TOKEN_MAX_AGE"])
    except SignatureExpired:
        flash("Ссылка подтверждения устарела. Запросите новую в личном профиле.", "error")
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
    if sent:
        flash("Письмо с подтверждением отправлено повторно.", "success")
    else:
        flash(f"Почтовый сервер не настроен, вот ссылка подтверждения: {confirm_url}", "info")
    return redirect(url_for("main.index"))


@bp.route("/choose-role", methods=["GET", "POST"])
@login_required
def choose_role():
    """Только для пользователей, впервые вошедших через Google — у них ещё
    нет роли (Google не сообщает, заказчик это или исполнитель)."""
    if current_user.role is not None:
        return _post_login_redirect()

    next_url = request.args.get("next") or request.form.get("next") or ""

    if request.method == "POST":
        role = request.form.get("role")
        if role not in ("customer", "executor"):
            flash("Выберите, вы заказчик или исполнитель.", "error")
            return render_template("auth/choose_role.html", next_url=next_url)
        current_user.role = role
        db.session.commit()
        flash("Роль сохранена.", "success")
        return _post_login_redirect()

    return render_template("auth/choose_role.html", next_url=next_url)


# --- Google OAuth ---

@bp.route("/google/login")
def google_login():
    google = get_google_client()
    if google is None:
        abort(404)
    redirect_uri = url_for("auth.google_callback", _external=True)
    nonce = generate_token()
    session["google_oauth_nonce"] = nonce
    session["google_oauth_next"] = request.args.get("next", "")
    return google.authorize_redirect(redirect_uri, nonce=nonce)


@bp.route("/google/callback")
def google_callback():
    google = get_google_client()
    if google is None:
        abort(404)

    token = google.authorize_access_token()
    nonce = session.pop("google_oauth_nonce", None)
    next_url = session.pop("google_oauth_next", "")

    userinfo = google.parse_id_token(token, nonce=nonce)
    email = (userinfo.get("email") or "").strip().lower()
    google_sub = userinfo.get("sub")

    if not email or not google_sub:
        flash("Google не передал email — вход невозможен.", "error")
        return redirect(url_for("main.index"))

    user = User.query.filter_by(google_sub=google_sub).first()
    if user is None:
        user = User.query.filter_by(email=email).first()
        if user is not None:
            user.google_sub = google_sub  # связываем существующий email-аккаунт с Google
        else:
            user = User(
                email=email,
                google_sub=google_sub,
                email_confirmed=bool(userinfo.get("email_verified", True)),
                confirmed_at=datetime.utcnow() if userinfo.get("email_verified", True) else None,
            )
            db.session.add(user)

    user.last_login_at = datetime.utcnow()
    db.session.commit()

    login_user(user)
    flash("Вы вошли через Google.", "success")

    if user.role is None:
        return redirect(url_for("auth.choose_role", next=next_url) if next_url else url_for("auth.choose_role"))
    if next_url:
        return redirect(next_url)
    return _post_login_redirect()
