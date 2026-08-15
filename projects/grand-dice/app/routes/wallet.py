"""Кошелёк: пополнение и вывод реальных средств.

Пока не подключён платёжный шлюз (Click API — запланирован отдельно),
и депозит, и вывод оформляются как заявки: администратор обрабатывает их
вручную в /admin. Вывод дополнительно защищён одноразовым кодом (OTP),
который отправляется на email и должен быть введён до того, как заявка
попадёт в очередь администратора.
"""
import secrets
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from werkzeug.security import check_password_hash, generate_password_hash

from app import db
from app.email import send_email
from app.models import User, WalletRequest

bp = Blueprint("wallet", __name__)

OTP_MAX_ATTEMPTS = 5


@bp.route("/")
@login_required
def index():
    requests_ = (
        WalletRequest.query.filter_by(user_id=current_user.id)
        .order_by(WalletRequest.created_at.desc())
        .limit(30)
        .all()
    )
    return render_template("wallet/index.html", requests=requests_)


@bp.route("/card", methods=["POST"])
@login_required
def save_card():
    card_number = (request.form.get("card_number") or "").strip()
    digits_only = card_number.replace(" ", "")

    if not digits_only.isdigit() or not (13 <= len(digits_only) <= 19):
        flash("Введите корректный номер карты (13-19 цифр).", "error")
        return redirect(url_for("wallet.index"))

    current_user.card_number = card_number
    db.session.commit()
    flash("Номер карты сохранён.", "success")
    return redirect(url_for("wallet.index"))


@bp.route("/deposit", methods=["POST"])
@login_required
def deposit():
    if not current_user.email_confirmed:
        flash("Подтвердите email, чтобы пополнять реальный баланс.", "error")
        return redirect(url_for("wallet.index"))

    try:
        amount = Decimal(str(request.form.get("amount"))).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError):
        flash("Некорректная сумма.", "error")
        return redirect(url_for("wallet.index"))

    min_amount = Decimal(str(current_app.config["MIN_DEPOSIT_AMOUNT"]))
    if amount < min_amount:
        flash(f"Минимальная сумма пополнения — {min_amount}.", "error")
        return redirect(url_for("wallet.index"))

    req = WalletRequest(user_id=current_user.id, kind="deposit", amount=amount, status="pending")
    db.session.add(req)
    db.session.commit()

    flash(
        "Заявка на пополнение создана. Оплата через Click появится здесь позже — "
        "пока администратор подтверждает пополнение вручную после получения оплаты.",
        "success",
    )
    return redirect(url_for("wallet.index"))


@bp.route("/withdraw/request", methods=["POST"])
@login_required
def withdraw_request():
    if not current_user.email_confirmed:
        flash("Подтвердите email, чтобы выводить реальные средства.", "error")
        return redirect(url_for("wallet.index"))

    if not current_user.card_number:
        flash("Сначала укажите номер карты для выплат.", "error")
        return redirect(url_for("wallet.index"))

    try:
        amount = Decimal(str(request.form.get("amount"))).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError):
        flash("Некорректная сумма.", "error")
        return redirect(url_for("wallet.index"))

    min_amount = Decimal(str(current_app.config["MIN_WITHDRAW_AMOUNT"]))
    if amount < min_amount:
        flash(f"Минимальная сумма вывода — {min_amount}.", "error")
        return redirect(url_for("wallet.index"))

    # Проверка, что нельзя вывести больше, чем реально есть на балансе.
    if amount > current_user.real_balance:
        flash("Недостаточно средств на реальном балансе.", "error")
        return redirect(url_for("wallet.index"))

    otp_code = f"{secrets.randbelow(1_000_000):06d}"
    req = WalletRequest(
        user_id=current_user.id,
        kind="withdraw",
        amount=amount,
        card_number=current_user.card_number,
        status="awaiting_otp",
        otp_hash=generate_password_hash(otp_code),
        otp_expires_at=datetime.utcnow() + timedelta(seconds=current_app.config["OTP_MAX_AGE"]),
    )
    db.session.add(req)
    db.session.commit()

    minutes = current_app.config["OTP_MAX_AGE"] // 60
    body = (
        f"Код подтверждения вывода {amount} со счёта Grand Dice Casino: {otp_code}\n\n"
        f"Код действителен {minutes} мин. Если вы не запрашивали вывод — "
        f"проигнорируйте это письмо и смените пароль."
    )
    sent = send_email(current_user.email, "Код подтверждения вывода средств", body)

    if sent:
        flash("Код подтверждения отправлен на email.", "success")
    else:
        flash(f"Почтовый сервер не настроен, вот код для теста: {otp_code}", "info")

    return redirect(url_for("wallet.withdraw_confirm", request_id=req.id))


@bp.route("/withdraw/confirm/<int:request_id>", methods=["GET", "POST"])
@login_required
def withdraw_confirm(request_id):
    req = WalletRequest.query.get_or_404(request_id)
    if req.user_id != current_user.id or req.kind != "withdraw":
        abort(404)

    if req.status != "awaiting_otp":
        flash("Эта заявка уже обработана.", "info")
        return redirect(url_for("wallet.index"))

    if req.otp_expires_at < datetime.utcnow():
        req.status = "rejected"
        req.admin_note = "Код подтверждения истёк."
        db.session.commit()
        flash("Код подтверждения истёк. Запросите вывод заново.", "error")
        return redirect(url_for("wallet.index"))

    if request.method == "POST":
        code = (request.form.get("code") or "").strip()

        if not check_password_hash(req.otp_hash, code):
            req.otp_attempts += 1
            if req.otp_attempts >= OTP_MAX_ATTEMPTS:
                req.status = "rejected"
                req.admin_note = "Превышено число попыток ввода кода."
                db.session.commit()
                flash("Слишком много неверных попыток. Запросите вывод заново.", "error")
                return redirect(url_for("wallet.index"))

            db.session.commit()
            flash("Неверный код.", "error")
            return render_template("wallet/withdraw_confirm.html", req=req)

        # Блокируем строку пользователя, чтобы баланс не мог измениться
        # между проверкой и списанием (например, если игрок в другой
        # вкладке успел сделать ставку).
        locked_user = db.session.query(User).filter_by(id=current_user.id).with_for_update().one()
        if req.amount > locked_user.real_balance:
            req.status = "rejected"
            req.admin_note = "На момент подтверждения средств уже не хватало."
            db.session.commit()
            flash("Средств на балансе уже не хватает для этого вывода.", "error")
            return redirect(url_for("wallet.index"))

        locked_user.real_balance -= req.amount
        req.status = "pending"
        db.session.commit()

        flash(
            "Код подтверждён, средства зарезервированы. Заявка передана "
            "администратору — выплата придёт после ручной обработки.",
            "success",
        )
        return redirect(url_for("wallet.index"))

    return render_template("wallet/withdraw_confirm.html", req=req)
