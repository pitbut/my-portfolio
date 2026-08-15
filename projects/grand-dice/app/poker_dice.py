"""Оценка комбинаций для режима «Покер на костях» (4 шестигранных кубика,
игрок против казино — казино тоже бросает 4 кубика).

Комбинации (от сильнейшей к слабейшей):
  Каре       — все 4 кубика одного значения.
  Сет        — 3 кубика одного значения + 1 любой.
  Стрит      — четыре кубика подряд (1-2-3-4, 2-3-4-5 или 3-4-5-6).
  Две пары   — два кубика одного значения + два другого.
  Пара       — ровно два кубика одного значения.
  Пусто      — ничего из вышеперечисленного, сравнение по старшей кости.

Игрок выигрывает, если его комбинация сильнее комбинации казино (при
равном ранге — сравниваются значения комбинации, например каре шестёрок
сильнее каре троек). Полное совпадение — ничья: ставка возвращается за
вычетом свопа (комиссии казино), как и во всех остальных играх.
"""
from collections import Counter
from decimal import Decimal
from itertools import product

HAND_NAMES = {
    5: "Каре",
    4: "Сет",
    3: "Стрит",
    2: "Две пары",
    1: "Пара",
    0: "Пусто",
}


def evaluate_hand(dice):
    """dice — последовательность из 4 целых 1-6.

    Возвращает dict {rank, tiebreak, label}. Сравнивать через compare_hands.
    """
    counts = Counter(dice)
    by_count = sorted(counts.items(), key=lambda kv: (-kv[1], -kv[0]))  # (значение, сколько раз)
    values_sorted = sorted(dice)
    is_straight = values_sorted in ([1, 2, 3, 4], [2, 3, 4, 5], [3, 4, 5, 6])
    top_count = by_count[0][1]

    if top_count == 4:
        rank, tiebreak = 5, (by_count[0][0],)
    elif top_count == 3:
        rank, tiebreak = 4, (by_count[0][0], by_count[1][0])
    elif is_straight:
        rank, tiebreak = 3, (values_sorted[-1],)
    elif top_count == 2 and len(by_count) >= 2 and by_count[1][1] == 2:
        rank = 2
        tiebreak = tuple(sorted([by_count[0][0], by_count[1][0]], reverse=True))
    elif top_count == 2:
        rank = 1
        kicker = tuple(sorted((v for v in dice if v != by_count[0][0]), reverse=True))
        tiebreak = (by_count[0][0], kicker)
    else:
        rank, tiebreak = 0, tuple(sorted(dice, reverse=True))

    return {"rank": rank, "tiebreak": tiebreak, "label": HAND_NAMES[rank]}


def compare_hands(hand_a, hand_b):
    """1, если a сильнее b; -1, если слабее; 0 — ничья (пуш)."""
    key_a = (hand_a["rank"], hand_a["tiebreak"])
    key_b = (hand_b["rank"], hand_b["tiebreak"])
    if key_a > key_b:
        return 1
    if key_a < key_b:
        return -1
    return 0


def _compute_win_probability():
    """Точная вероятность выигрыша игрока против случайной руки казино,
    посчитанная перебором всех 6^4 x 6^4 исходов один раз при импорте
    модуля (комбинаций мало, перебор мгновенный)."""
    keys = [
        (evaluate_hand(dice)["rank"], evaluate_hand(dice)["tiebreak"])
        for dice in product(range(1, 7), repeat=4)
    ]
    total = len(keys)
    counts = Counter(keys)
    win_pairs = 0
    for key_a, count_a in counts.items():
        for key_b, count_b in counts.items():
            if key_a > key_b:
                win_pairs += count_a * count_b
    return Decimal(win_pairs) / Decimal(total * total)


FOUR_DICE_WIN_PROBABILITY = _compute_win_probability()
