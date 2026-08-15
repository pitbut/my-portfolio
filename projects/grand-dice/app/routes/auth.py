"""Регистрация, вход и подтверждение email."""
import re
from datetime import datetime
from decimal import Decimal

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
        f"Подтвердите регистрацию в Grand Dice Casino, перейдя по ссылке:\n"
        f"{confirm_url}\n\n"
        f"Ссылка действительна {current_app.config['CONFIRM_TOKEN_MAX_AGE'] // 3600} часов. "
        f"Если вы не регистрировались — просто проигнорируйте это письмо."
    )
    sent = send_email(user.email, "Подтверждение регистрации — Grand Dice Casino", body)
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

        user = User(
            email=email,
            password_hash=generate_password_hash(password),
            demo_balance=Decimal(current_app.config["STARTING_DEMO_BALANCE"]),
        )
        db.session.add(user)
        db.session.commit()

        login_user(user)

        sent, confirm_url = _send_confirmation_email(user)
        if sent:
            flash(
                "Регистрация почти завершена — мы отправили письмо со ссылкой "
                "подтверждения на ваш email. Играть в демо-режиме можно и до "
                "подтверждения, а для ставок на реальные деньги оно потребуется.",
                "success",
            )
        else:
            flash(
                f"Регистрация завершена. Почтовый сервер ещё не настроен, поэтому "
                f"подтвердите email по этой ссылке: {confirm_url}",
                "info",
            )
        return redirect(url_for("game.play_page"))

    return render_template("auth/register.html", email="")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        user = User.query.filter_by(email=email).first()
        if user is None or not check_password_hash(user.password_hash, password):
            flash("Неверный email или пароль.", "error")
            return render_template("auth/login.html", email=email)

        login_user(user)
        flash("Вы вошли в аккаунт.", "success")
        return redirect(request.args.get("next") or url_for("game.play_page"))

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

    flash("Email подтверждён, теперь доступны ставки на реальные деньги.", "success")
    return redirect(url_for("game.play_page"))


@bp.route("/resend-confirmation")
@login_required
def resend_confirmation():
    if current_user.email_confirmed:
        flash("Email уже подтверждён.", "info")
        return redirect(url_for("game.play_page"))

    sent, confirm_url = _send_confirmation_email(current_user)
    if sent:
        flash("Письмо с подтверждением отправлено повторно.", "success")
    else:
        flash(f"Почтовый сервер не настроен, вот ссылка подтверждения: {confirm_url}", "info")
    return redirect(url_for("game.play_page"))


def reset_url_for(user):
    token = _serializer().dumps(user.email, salt=RESET_SALT)
    return url_for("auth.reset_password", token=token, _external=True)


def _send_reset_email(user):
    reset_url = reset_url_for(user)
    body = (
        f"Здравствуйте!\n\n"
        f"Чтобы установить новый пароль в Grand Dice Casino, перейдите по ссылке:\n"
        f"{reset_url}\n\n"
        f"Ссылка действительна {current_app.config['RESET_TOKEN_MAX_AGE'] // 60} минут. "
        f"Если вы не запрашивали смену пароля — просто проигнорируйте это письмо, "
        f"пароль останется прежним."
    )
    sent = send_email(user.email, "Восстановление пароля — Grand Dice Casino", body)
    return sent, reset_url


@bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        user = User.query.filter_by(email=email).first()

        # Одинаковый ответ независимо от того, найден пользователь или нет —
        # иначе форма превращается в способ проверить, кто зарегистрирован.
        generic_message = (
            "Если такой email зарегистрирован, на него отправлена ссылка "
            "для восстановления пароля."
        )

        if user is None:
            flash(generic_message, "info")
            return redirect(url_for("auth.login"))

        sent, reset_url = _send_reset_email(user)
        if sent:
            flash(generic_message, "info")
        else:
            flash(
                f"Почтовый сервер не настроен, вот ссылка для сброса пароля: {reset_url}",
                "info",
            )
        return redirect(url_for("auth.login"))

    return render_template("auth/forgot_password.html")


@bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    try:
        email = _serializer().loads(
            token, salt=RESET_SALT, max_age=current_app.config["RESET_TOKEN_MAX_AGE"]
        )
    except SignatureExpired:
        flash("Ссылка для сброса пароля устарела. Запросите новую.", "error")
        return redirect(url_for("auth.forgot_password"))
    except BadSignature:
        flash("Ссылка для сброса пароля недействительна.", "error")
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

        flash("Пароль изменён. Теперь можно войти с новым паролем.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/reset_password.html", token=token)
