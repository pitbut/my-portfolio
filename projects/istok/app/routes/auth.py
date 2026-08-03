"""Регистрация, вход и подтверждение email для обычных пользователей."""
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


def _send_confirmation_email(user):
    token = _serializer().dumps(user.email, salt=CONFIRM_SALT)
    confirm_url = url_for("auth.confirm_email", token=token, _external=True)
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
        if user is None or not check_password_hash(user.password_hash, password):
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
