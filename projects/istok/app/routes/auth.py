"""Регистрация, вход и подтверждение email для обычных пользователей."""
import re
from datetime import datetime

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash

from app import db, oauth
from app.email import send_email
from app.models import User

bp = Blueprint("auth", __name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
CONFIRM_SALT = "email-confirm"
RESET_SALT = "password-reset"


def _serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"])


def confirm_url_for(user):
    """Строит ссылку подтверждения для пользователя (без отправки письма)."""
    token = _serializer().dumps(user.email, salt=CONFIRM_SALT)
    return url_for("auth.confirm_email", token=token, _external=True)


def _send_confirmation_email(user):
    confirm_url = confirm_url_for(user)
    body = (
        f"Здравствуйте!\n\n"
        f"Подтвердите регистрацию на портале «Исток», перейдя по ссылке:\n"
        f"{confirm_url}\n\n"
        f"Ссылка действительна {current_app.config['CONFIRM_TOKEN_MAX_AGE'] // 3600} часов. "
        f"Если вы не регистрировались на сайте — просто проигнорируйте это письмо."
    )
    sent = send_email(user.email, "Подтверждение регистрации — Исток", body)
    return sent, confirm_url


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        password2 = request.form.get("password2") or ""

        if not EMAIL_RE.match(email):
            flash("Введите корректный email.", "error")
            return render_template("auth/register.html", email=email)
        if len(password) < 8:
            flash("Пароль должен быть не короче 8 символов.", "error")
            return render_template("auth/register.html", email=email)
        if password != password2:
            flash("Пароли не совпадают.", "error")
            return render_template("auth/register.html", email=email)
        if User.query.filter_by(email=email).first() is not None:
            flash("Этот email уже зарегистрирован. Попробуйте войти.", "error")
            return render_template("auth/register.html", email=email)

        user = User(email=email, password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()

        login_user(user)

        sent, confirm_url = _send_confirmation_email(user)
        if sent:
            flash("Регистрация почти завершена — мы отправили письмо со ссылкой подтверждения на ваш email.", "success")
        else:
            # SMTP не настроен на сервере — показываем ссылку прямо на странице,
            # чтобы регистрация не блокировалась.
            flash(
                f"Регистрация завершена. Почтовый сервер ещё не настроен, поэтому "
                f"подтвердите email по этой ссылке: {confirm_url}",
                "info",
            )
        return redirect(url_for("main.index"))

    return render_template("auth/register.html", email="")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        user = User.query.filter_by(email=email).first()
        if user is None or user.password_hash is None:
            flash("Неверный email или пароль.", "error")
            return render_template("auth/login.html", email=email)
        if not check_password_hash(user.password_hash, password):
            flash("Неверный email или пароль.", "error")
            return render_template("auth/login.html", email=email)

        login_user(user)
        flash("Вы вошли на сайт.", "success")
        return redirect(request.args.get("next") or url_for("main.index"))

    return render_template("auth/login.html", email="")


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Вы вышли из аккаунта.", "info")
    return redirect(url_for("main.index"))


@bp.route("/google/login")
def google_login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    if not current_app.config.get("GOOGLE_CLIENT_ID"):
        flash("Вход через Google сейчас недоступен.", "error")
        return redirect(url_for("auth.login"))

    redirect_uri = url_for("auth.google_callback", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@bp.route("/google/callback")
def google_callback():
    if not current_app.config.get("GOOGLE_CLIENT_ID"):
        flash("Вход через Google сейчас недоступен.", "error")
        return redirect(url_for("auth.login"))

    token = oauth.google.authorize_access_token()
    userinfo = token.get("userinfo") or oauth.google.userinfo(token=token)
    email = (userinfo.get("email") or "").strip().lower()
    google_id = userinfo.get("sub")

    if not email or not google_id:
        flash("Google не передал email аккаунта. Попробуйте войти другим способом.", "error")
        return redirect(url_for("auth.login"))

    user = User.query.filter_by(google_id=google_id).first()
    if user is None:
        # Тот же email уже мог быть зарегистрирован через пароль — просто
        # привязываем Google к существующему аккаунту, а не заводим дубль.
        user = User.query.filter_by(email=email).first()
        if user is None:
            user = User(email=email, google_id=google_id)
            db.session.add(user)
        else:
            user.google_id = google_id
        if userinfo.get("email_verified") and not user.email_confirmed:
            user.email_confirmed = True
            user.confirmed_at = datetime.utcnow()
        db.session.commit()

    login_user(user)
    flash("Вы вошли через Google.", "success")
    return redirect(request.args.get("next") or url_for("main.index"))


@bp.route("/confirm/<token>")
def confirm_email(token):
    try:
        email = _serializer().loads(
            token, salt=CONFIRM_SALT, max_age=current_app.config["CONFIRM_TOKEN_MAX_AGE"]
        )
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


@bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        user = User.query.filter_by(email=email).first()

        if user is not None:
            token = _serializer().dumps(user.email, salt=RESET_SALT)
            reset_url = url_for("auth.reset_password", token=token, _external=True)
            body = (
                f"Здравствуйте!\n\n"
                f"Вы (или кто-то другой) запросили восстановление пароля на портале «Исток». "
                f"Чтобы задать новый пароль, перейдите по ссылке:\n"
                f"{reset_url}\n\n"
                f"Ссылка действительна {current_app.config['PASSWORD_RESET_TOKEN_MAX_AGE'] // 60} минут. "
                f"Если вы не запрашивали восстановление — просто проигнорируйте это письмо."
            )
            sent = send_email(user.email, "Восстановление пароля — Исток", body)
            if not sent:
                # Почтовый сервер не настроен — показываем ссылку прямо на странице,
                # как и в остальных местах сайта с этим же запасным вариантом.
                flash(f"Почтовый сервер не настроен, вот ссылка для сброса пароля: {reset_url}", "info")
                return redirect(url_for("auth.login"))

        # Один и тот же ответ независимо от того, найден ли email — чтобы не
        # показывать, зарегистрирован ли конкретный адрес на сайте.
        flash("Если такой email зарегистрирован, на него отправлена ссылка для восстановления пароля.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/forgot_password.html", email="")


@bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    try:
        email = _serializer().loads(
            token, salt=RESET_SALT, max_age=current_app.config["PASSWORD_RESET_TOKEN_MAX_AGE"]
        )
    except SignatureExpired:
        flash("Ссылка для восстановления пароля устарела. Запросите новую.", "error")
        return redirect(url_for("auth.forgot_password"))
    except BadSignature:
        flash("Ссылка для восстановления пароля недействительна.", "error")
        return redirect(url_for("auth.forgot_password"))

    user = User.query.filter_by(email=email).first()
    if user is None:
        flash("Пользователь не найден.", "error")
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        password = request.form.get("password") or ""
        password2 = request.form.get("password2") or ""

        if len(password) < 8:
            flash("Пароль должен быть не короче 8 символов.", "error")
            return render_template("auth/reset_password.html", token=token)
        if password != password2:
            flash("Пароли не совпадают.", "error")
            return render_template("auth/reset_password.html", token=token)

        user.password_hash = generate_password_hash(password)
        db.session.commit()
        login_user(user)
        flash("Пароль изменён, вы вошли на сайт.", "success")
        return redirect(url_for("main.index"))

    return render_template("auth/reset_password.html", token=token)
