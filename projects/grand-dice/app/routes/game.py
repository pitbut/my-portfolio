"""Игра в кости: страница и обработка ставок."""
from decimal import Decimal, InvalidOperation

from flask import Blueprint, current_app, jsonify, render_template, request, session
from flask_login import current_user, login_required

from app import db
from app.dice import resolve_round, validate_target
from app.models import GameRound

bp = Blueprint("game", __name__)

MAX_BET = Decimal("100000")
MIN_BET = Decimal("1")


def _current_mode():
    """Режим ставок текущей сессии: 'real' или 'demo'. По умолчанию demo,
    чтобы новый/неподтверждённый пользователь мог сразу играть без риска."""
    return session.get("play_mode", "demo")


@bp.route("/")
@login_required
def play_page():
    history = (
        GameRound.query.filter_by(user_id=current_user.id)
        .order_by(GameRound.created_at.desc())
        .limit(20)
        .all()
    )
    return render_template(
        "game/play.html",
        mode=_current_mode(),
        history=history,
        house_edge=current_app.config["HOUSE_EDGE_PERCENT"],
    )


@bp.route("/mode", methods=["POST"])
@login_required
def set_mode():
    mode = request.form.get("mode")
    if mode not in ("real", "demo"):
        return jsonify({"ok": False, "error": "Некорректный режим."}), 400

    if mode == "real" and not current_user.email_confirmed:
        return jsonify({
            "ok": False,
            "error": "Подтвердите email, чтобы играть на реальные деньги.",
        }), 403

    session["play_mode"] = mode
    return jsonify({"ok": True, "mode": mode, "balance": str(current_user.balance_for(mode))})


@bp.route("/play", methods=["POST"])
@login_required
def play():
    mode = _current_mode()
    if mode == "real" and not current_user.email_confirmed:
        return jsonify({"ok": False, "error": "Подтвердите email, чтобы играть на реальные деньги."}), 403

    direction = request.form.get("direction")
    if direction not in ("under", "over"):
        return jsonify({"ok": False, "error": "Некорректное направление ставки."}), 400

    try:
        target = validate_target(request.form.get("target"))
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400

    try:
        bet_amount = Decimal(str(request.form.get("bet_amount"))).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError):
        return jsonify({"ok": False, "error": "Некорректная сумма ставки."}), 400

    if bet_amount < MIN_BET or bet_amount > MAX_BET:
        return jsonify({"ok": False, "error": f"Ставка должна быть от {MIN_BET} до {MAX_BET}."}), 400

    # Блокируем строку пользователя на время расчёта ставки, чтобы два
    # параллельных запроса (например, из двух вкладок) не прочитали один и
    # тот же баланс и не потеряли списание. На SQLite (локальная разработка)
    # FOR UPDATE молча игнорируется — там и так один писатель одновременно.
    from app.models import User
    locked_user = db.session.query(User).filter_by(id=current_user.id).with_for_update().one()

    balance = locked_user.balance_for(mode)
    if bet_amount > balance:
        return jsonify({"ok": False, "error": "Недостаточно средств на балансе."}), 400

    result = resolve_round(direction, target, bet_amount, current_app.config["HOUSE_EDGE_PERCENT"])

    new_balance = balance - bet_amount + result["payout"]
    if mode == "real":
        locked_user.real_balance = new_balance
    else:
        locked_user.demo_balance = new_balance

    round_ = GameRound(
        user_id=current_user.id,
        mode=mode,
        direction=direction,
        target=target,
        roll=result["roll"],
        bet_amount=bet_amount,
        multiplier=result["multiplier"],
        payout=result["payout"],
        win=result["win"],
    )
    db.session.add(round_)
    db.session.commit()

    return jsonify({
        "ok": True,
        "roll": str(result["roll"]),
        "win": result["win"],
        "multiplier": str(result["multiplier"]),
        "payout": str(result["payout"]),
        "balance": str(new_balance),
        "mode": mode,
    })
