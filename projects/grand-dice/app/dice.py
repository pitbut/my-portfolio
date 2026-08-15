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
