"""Логика игры в кости: бросок и расчёт выплаты.

Классическая механика "roll under/over": игрок выбирает порог (2-98) и
направление. Шанс выигрыша — это доля диапазона 0.00-99.99, которая
попадает под условие. Множитель выплаты считается из шанса выигрыша и
комиссии казино (house edge), как в обычных crypto-dice играх.

Бросок делается через `secrets` (криптостойкий генератор), а не `random` —
это на стороне сервера и игроку недоступно до расчёта раунда, так что
подделать его нельзя.
"""
from decimal import Decimal, ROUND_DOWN
import secrets

MIN_TARGET = Decimal("2.00")
MAX_TARGET = Decimal("98.00")


def roll_dice():
    """Возвращает криптостойкое случайное число 0.00-99.99."""
    return Decimal(secrets.randbelow(10000)) / Decimal(100)


def win_chance_percent(direction, target):
    """Доля (в процентах) значений броска, при которых ставка выигрывает."""
    if direction == "under":
        return target
    return Decimal(100) - target


def payout_multiplier(direction, target, house_edge_percent):
    """Множитель выплаты при выигрыше (bet * multiplier = payout)."""
    chance = win_chance_percent(direction, target)
    house_edge = Decimal(str(house_edge_percent))
    multiplier = (Decimal(100) - house_edge) / chance
    return multiplier.quantize(Decimal("0.0001"), rounding=ROUND_DOWN)


def resolve_round(direction, target, bet_amount, house_edge_percent):
    """Бросает кости и считает результат одного раунда.

    Возвращает dict с roll, multiplier, win, payout — всё в Decimal,
    готовое для сохранения в GameRound и применения к балансу.
    """
    roll = roll_dice()
    multiplier = payout_multiplier(direction, target, house_edge_percent)

    if direction == "under":
        win = roll < target
    else:
        win = roll > target

    payout = (bet_amount * multiplier).quantize(Decimal("0.01"), rounding=ROUND_DOWN) if win else Decimal("0.00")

    return {
        "roll": roll,
        "multiplier": multiplier,
        "win": win,
        "payout": payout,
    }


def validate_target(raw_target):
    """Проверяет и нормализует порог ставки. Бросает ValueError, если он вне диапазона."""
    try:
        target = Decimal(str(raw_target)).quantize(Decimal("0.01"))
    except Exception as exc:
        raise ValueError("Некорректное число.") from exc

    if target < MIN_TARGET or target > MAX_TARGET:
        raise ValueError(f"Порог должен быть от {MIN_TARGET} до {MAX_TARGET}.")

    return target


# --- Режим "Два кубика" (2d6) ---
#
# Игрок выбирает порог-сумму (3-11) и направление (больше/меньше). Если
# сумма выпавших костей ТОЧНО равна порогу — это ничья с казино (пуш):
# ставка возвращается за вычетом свопа, а не проигрывается. Это стандартная
# механика ставок на сумму двух костей (как в крэпсе), выбрана специально,
# чтобы естественно завести в игру правило "ничья с казино" из ТЗ.

TWO_DICE_MIN_TARGET = 3
TWO_DICE_MAX_TARGET = 11


def _combos_for_sum(total):
    return sum(1 for a in range(1, 7) for b in range(1, 7) if a + b == total)


TWO_DICE_COMBO_COUNTS = {s: _combos_for_sum(s) for s in range(2, 13)}  # из 36


def roll_two_dice():
    return secrets.randbelow(6) + 1, secrets.randbelow(6) + 1


def two_dice_win_chance_percent(direction, target):
    """Доля исходов (в процентах из 36), которые выигрывают — исключая
    исходы, равные порогу (те считаются ничьей, не выигрышем)."""
    if direction == "under":
        favorable = sum(TWO_DICE_COMBO_COUNTS[s] for s in range(2, target))
    else:
        favorable = sum(TWO_DICE_COMBO_COUNTS[s] for s in range(target + 1, 13))
    return (Decimal(favorable) / Decimal(36)) * Decimal(100)


def two_dice_payout_multiplier(direction, target, house_edge_percent):
    chance = two_dice_win_chance_percent(direction, target)
    house_edge = Decimal(str(house_edge_percent))
    multiplier = (Decimal(100) - house_edge) / chance
    return multiplier.quantize(Decimal("0.0001"), rounding=ROUND_DOWN)


def _push_payout(bet_amount, house_edge_percent):
    """Возврат ставки при ничьей — за вычетом свопа (комиссии казино)."""
    house_edge = Decimal(str(house_edge_percent))
    return (bet_amount * (Decimal(100) - house_edge) / Decimal(100)).quantize(
        Decimal("0.01"), rounding=ROUND_DOWN
    )


def resolve_two_dice_round(direction, target, bet_amount, house_edge_percent):
    d1, d2 = roll_two_dice()
    total = d1 + d2
    multiplier = two_dice_payout_multiplier(direction, target, house_edge_percent)

    if total == target:
        outcome = "push"
    elif (direction == "under" and total < target) or (direction == "over" and total > target):
        outcome = "win"
    else:
        outcome = "lose"

    if outcome == "win":
        payout = (bet_amount * multiplier).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
    elif outcome == "push":
        payout = _push_payout(bet_amount, house_edge_percent)
    else:
        payout = Decimal("0.00")

    return {"dice": (d1, d2), "roll": total, "multiplier": multiplier, "outcome": outcome, "payout": payout}


def validate_two_dice_target(raw_target):
    try:
        target = int(raw_target)
    except (TypeError, ValueError) as exc:
        raise ValueError("Некорректное число.") from exc

    if target < TWO_DICE_MIN_TARGET or target > TWO_DICE_MAX_TARGET:
        raise ValueError(f"Порог должен быть от {TWO_DICE_MIN_TARGET} до {TWO_DICE_MAX_TARGET}.")

    return target


# --- Режим "Покер на костях" (4 кубика, игрок против казино) ---

def roll_four_dice():
    return tuple(secrets.randbelow(6) + 1 for _ in range(4))


def four_dice_payout_multiplier(house_edge_percent):
    from app.poker_dice import FOUR_DICE_WIN_PROBABILITY

    win_chance_percent = FOUR_DICE_WIN_PROBABILITY * Decimal(100)
    house_edge = Decimal(str(house_edge_percent))
    multiplier = (Decimal(100) - house_edge) / win_chance_percent
    return multiplier.quantize(Decimal("0.0001"), rounding=ROUND_DOWN)


def resolve_four_dice_round(bet_amount, house_edge_percent):
    from app.poker_dice import compare_hands, evaluate_hand

    player_dice = roll_four_dice()
    dealer_dice = roll_four_dice()
    player_hand = evaluate_hand(player_dice)
    dealer_hand = evaluate_hand(dealer_dice)
    cmp = compare_hands(player_hand, dealer_hand)

    multiplier = four_dice_payout_multiplier(house_edge_percent)

    if cmp > 0:
        outcome = "win"
        payout = (bet_amount * multiplier).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
    elif cmp == 0:
        outcome = "push"
        payout = _push_payout(bet_amount, house_edge_percent)
    else:
        outcome = "lose"
        payout = Decimal("0.00")

    return {
        "player_dice": list(player_dice),
        "dealer_dice": list(dealer_dice),
        "player_hand": player_hand,
        "dealer_hand": dealer_hand,
        "outcome": outcome,
        "multiplier": multiplier,
        "payout": payout,
    }
