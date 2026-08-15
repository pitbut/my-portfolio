"""Игры в кости: классика (1 кость), два кубика, покер на костях (4 кубика)."""
import json
from datetime import datetime
from decimal import ROUND_DOWN, Decimal, InvalidOperation

from flask import Blueprint, current_app, jsonify, render_template, request, session
from flask_login import current_user, login_required

from app import db
from app.betting import apply_loss_limit_check, apply_round_to_house_bank, check_house_can_cover, check_real_play_allowed
from app.dice import (
    four_dice_payout_multiplier,
    payout_multiplier,
    resolve_four_dice_round,
    resolve_round,
    resolve_two_dice_round,
    two_dice_payout_multiplier,
    validate_target,
    validate_two_dice_target,
)
from app.models import GameRound, User

bp = Blueprint("game", __name__)

MAX_BET = Decimal("100000")
MIN_BET = Decimal("1")


def _current_mode():
    """Режим ставок текущей сессии: 'real' или 'demo'. По умолчанию demo,
    чтобы новый/неподтверждённый пользователь мог сразу играть без риска."""
    return session.get("play_mode", "demo")


def _parse_bet_amount():
    try:
        amount = Decimal(str(request.form.get("bet_amount"))).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError):
        raise ValueError("Некорректная сумма ставки.")
    if amount < MIN_BET or amount > MAX_BET:
        raise ValueError(f"Ставка должна быть от {MIN_BET} до {MAX_BET}.")
    return amount


@bp.route("/")
@login_required
def play_page():
    history = (
        GameRound.query.filter_by(user_id=current_user.id, game_type="classic")
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

    if mode == "real":
        if not current_user.email_confirmed:
            return jsonify({
                "ok": False,
                "error": "Подтвердите email, чтобы играть на реальные деньги.",
            }), 403
        if current_user.real_play_locked_until and current_user.real_play_locked_until > datetime.utcnow():
            until = current_user.real_play_locked_until.strftime("%H:%M")
            return jsonify({
                "ok": False,
                "error": f"Реальная игра заблокирована до {until} UTC (лимит проигрыша за сессию).",
            }), 403
        # Новая "сессия" реальной игры начинается здесь — от этого баланса
        # считается % проигрыша для автоблокировки (см. app/betting.py).
        current_user.session_start_balance = current_user.real_balance
        db.session.commit()

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
        bet_amount = _parse_bet_amount()
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400

    # Блокируем строку пользователя на время расчёта ставки, чтобы два
    # параллельных запроса (например, из двух вкладок) не прочитали один и
    # тот же баланс и не потеряли списание. На SQLite (локальная разработка)
    # FOR UPDATE молча игнорируется — там и так один писатель одновременно.
    locked_user = db.session.query(User).filter_by(id=current_user.id).with_for_update().one()

    balance = locked_user.balance_for(mode)
    if bet_amount > balance:
        return jsonify({"ok": False, "error": "Недостаточно средств на балансе."}), 400

    settings = None
    if mode == "real":
        try:
            settings = check_real_play_allowed(locked_user)
            multiplier = payout_multiplier(direction, target, current_app.config["HOUSE_EDGE_PERCENT"])
            potential_payout = (bet_amount * multiplier).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
            check_house_can_cover(settings, bet_amount, potential_payout)
        except ValueError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 403

    result = resolve_round(direction, target, bet_amount, current_app.config["HOUSE_EDGE_PERCENT"])

    new_balance = balance - bet_amount + result["payout"]
    if mode == "real":
        locked_user.real_balance = new_balance
        apply_round_to_house_bank(settings, bet_amount, result["payout"])
        apply_loss_limit_check(locked_user, settings)
    else:
        locked_user.demo_balance = new_balance

    round_ = GameRound(
        user_id=current_user.id,
        mode=mode,
        game_type="classic",
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

    response = {
        "ok": True,
        "roll": str(result["roll"]),
        "win": result["win"],
        "multiplier": str(result["multiplier"]),
        "payout": str(result["payout"]),
        "balance": str(new_balance),
        "mode": mode,
    }
    if mode == "real" and locked_user.real_play_locked_until:
        response["locked_until"] = locked_user.real_play_locked_until.strftime("%H:%M")
    return jsonify(response)


# --- Два кубика (2d6) ---

@bp.route("/two-dice")
@login_required
def two_dice_page():
    history = (
        GameRound.query.filter_by(user_id=current_user.id, game_type="two_dice")
        .order_by(GameRound.created_at.desc())
        .limit(20)
        .all()
    )
    history_view = []
    for r in history:
        dice = json.loads(r.dice_json) if r.dice_json else []
        history_view.append({"round": r, "dice": dice})

    return render_template(
        "game/two_dice.html",
        mode=_current_mode(),
        history=history_view,
        house_edge=current_app.config["HOUSE_EDGE_PERCENT"],
    )


@bp.route("/two-dice/play", methods=["POST"])
@login_required
def two_dice_play():
    mode = _current_mode()
    if mode == "real" and not current_user.email_confirmed:
        return jsonify({"ok": False, "error": "Подтвердите email, чтобы играть на реальные деньги."}), 403

    direction = request.form.get("direction")
    if direction not in ("under", "over"):
        return jsonify({"ok": False, "error": "Некорректное направление ставки."}), 400

    try:
        target = validate_two_dice_target(request.form.get("target"))
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400

    try:
        bet_amount = _parse_bet_amount()
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400

    locked_user = db.session.query(User).filter_by(id=current_user.id).with_for_update().one()
    balance = locked_user.balance_for(mode)
    if bet_amount > balance:
        return jsonify({"ok": False, "error": "Недостаточно средств на балансе."}), 400

    settings = None
    if mode == "real":
        try:
            settings = check_real_play_allowed(locked_user)
            multiplier = two_dice_payout_multiplier(direction, target, current_app.config["HOUSE_EDGE_PERCENT"])
            potential_payout = (bet_amount * multiplier).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
            check_house_can_cover(settings, bet_amount, potential_payout)
        except ValueError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 403

    result = resolve_two_dice_round(direction, target, bet_amount, current_app.config["HOUSE_EDGE_PERCENT"])

    new_balance = balance - bet_amount + result["payout"]
    if mode == "real":
        locked_user.real_balance = new_balance
        apply_round_to_house_bank(settings, bet_amount, result["payout"])
        apply_loss_limit_check(locked_user, settings)
    else:
        locked_user.demo_balance = new_balance

    round_ = GameRound(
        user_id=current_user.id,
        mode=mode,
        game_type="two_dice",
        direction=direction,
        target=Decimal(target),
        roll=Decimal(result["roll"]),
        bet_amount=bet_amount,
        multiplier=result["multiplier"],
        payout=result["payout"],
        win=(result["outcome"] == "win"),
        push=(result["outcome"] == "push"),
        dice_json=json.dumps(list(result["dice"])),
    )
    db.session.add(round_)
    db.session.commit()

    response = {
        "ok": True,
        "dice": list(result["dice"]),
        "roll": result["roll"],
        "outcome": result["outcome"],
        "multiplier": str(result["multiplier"]),
        "payout": str(result["payout"]),
        "balance": str(new_balance),
        "mode": mode,
    }
    if mode == "real" and locked_user.real_play_locked_until:
        response["locked_until"] = locked_user.real_play_locked_until.strftime("%H:%M")
    return jsonify(response)


# --- Покер на костях (4 кубика, против казино) ---

@bp.route("/four-dice")
@login_required
def four_dice_page():
    history = (
        GameRound.query.filter_by(user_id=current_user.id, game_type="four_dice")
        .order_by(GameRound.created_at.desc())
        .limit(20)
        .all()
    )
    from app.poker_dice import FOUR_DICE_WIN_PROBABILITY

    history_view = []
    for r in history:
        detail = json.loads(r.dice_json) if r.dice_json else {}
        history_view.append({"round": r, "detail": detail})

    return render_template(
        "game/four_dice.html",
        mode=_current_mode(),
        history=history_view,
        house_edge=current_app.config["HOUSE_EDGE_PERCENT"],
        win_chance=str((FOUR_DICE_WIN_PROBABILITY * Decimal(100)).quantize(Decimal("0.01"))),
    )


@bp.route("/four-dice/play", methods=["POST"])
@login_required
def four_dice_play():
    mode = _current_mode()
    if mode == "real" and not current_user.email_confirmed:
        return jsonify({"ok": False, "error": "Подтвердите email, чтобы играть на реальные деньги."}), 403

    try:
        bet_amount = _parse_bet_amount()
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400

    locked_user = db.session.query(User).filter_by(id=current_user.id).with_for_update().one()
    balance = locked_user.balance_for(mode)
    if bet_amount > balance:
        return jsonify({"ok": False, "error": "Недостаточно средств на балансе."}), 400

    multiplier = four_dice_payout_multiplier(current_app.config["HOUSE_EDGE_PERCENT"])
    potential_payout = (bet_amount * multiplier).quantize(Decimal("0.01"), rounding=ROUND_DOWN)

    settings = None
    if mode == "real":
        try:
            settings = check_real_play_allowed(locked_user)
            check_house_can_cover(settings, bet_amount, potential_payout)
        except ValueError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 403

    result = resolve_four_dice_round(bet_amount, current_app.config["HOUSE_EDGE_PERCENT"])

    new_balance = balance - bet_amount + result["payout"]
    if mode == "real":
        locked_user.real_balance = new_balance
        apply_round_to_house_bank(settings, bet_amount, result["payout"])
        apply_loss_limit_check(locked_user, settings)
    else:
        locked_user.demo_balance = new_balance

    round_ = GameRound(
        user_id=current_user.id,
        mode=mode,
        game_type="four_dice",
        bet_amount=bet_amount,
        multiplier=result["multiplier"],
        payout=result["payout"],
        win=(result["outcome"] == "win"),
        push=(result["outcome"] == "push"),
        dice_json=json.dumps({
            "player": result["player_dice"],
            "dealer": result["dealer_dice"],
            "player_hand": result["player_hand"]["label"],
            "dealer_hand": result["dealer_hand"]["label"],
        }),
    )
    db.session.add(round_)
    db.session.commit()

    response = {
        "ok": True,
        "player_dice": result["player_dice"],
        "dealer_dice": result["dealer_dice"],
        "player_hand": result["player_hand"]["label"],
        "dealer_hand": result["dealer_hand"]["label"],
        "outcome": result["outcome"],
        "multiplier": str(result["multiplier"]),
        "payout": str(result["payout"]),
        "balance": str(new_balance),
        "mode": mode,
    }
    if mode == "real" and locked_user.real_play_locked_until:
        response["locked_until"] = locked_user.real_play_locked_until.strftime("%H:%M")
    return jsonify(response)
