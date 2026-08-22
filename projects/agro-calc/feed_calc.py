# -*- coding: utf-8 -*-
"""Расчёт норм кормления: прямой (по поголовью -> сколько корма нужно) и
обратный (по имеющемуся корму или желаемому результату -> сколько поголовья
потянуть / докупить)."""
import math

from norms import ANIMALS, FEED_TYPES


def compute_ration_per_head(animal_id, weight_kg, output_per_head, regime):
    """ЭКЕ/сутки и раскладку корма (кг/сутки) на одну голову."""
    animal = ANIMALS[animal_id]
    maintenance = animal["maintenance_efu_per_100kg"] * (weight_kg / 100.0)
    production = animal["production"]["efu_per_unit"] * output_per_head
    total_efu = maintenance + production

    ration = animal["rations"][regime]
    feed_kg = {}
    for feed_id, share in ration.items():
        efu_share = total_efu * share
        efu_per_kg = FEED_TYPES[feed_id]["efu_per_kg"]
        feed_kg[feed_id] = efu_share / efu_per_kg if efu_per_kg else 0.0

    return {
        "maintenance_efu": maintenance,
        "production_efu": production,
        "total_efu_per_head": total_efu,
        "feed_kg_per_head": feed_kg,
    }


def forward(animal_id, weight_kg, output_per_head, regime, count, days):
    """По поголовью, живой массе и продуктивности — сколько корма нужно
    на голову в сутки и всего на весь период."""
    per_head = compute_ration_per_head(animal_id, weight_kg, output_per_head, regime)

    feed_kg_total_period = {
        feed_id: kg_per_head * count * days
        for feed_id, kg_per_head in per_head["feed_kg_per_head"].items()
    }
    feed_kg_total_day = {
        feed_id: kg_per_head * count
        for feed_id, kg_per_head in per_head["feed_kg_per_head"].items()
    }

    return {
        "animal_id": animal_id,
        "count": count,
        "days": days,
        "weight_kg": weight_kg,
        "regime": regime,
        "output_per_head": output_per_head,
        "per_head": per_head,
        "total_efu_per_day_all": per_head["total_efu_per_head"] * count,
        "total_efu_period_all": per_head["total_efu_per_head"] * count * days,
        "feed_kg_per_day_all": feed_kg_total_day,
        "feed_kg_period_all": feed_kg_total_period,
        "feed_kg_per_head_period": {
            feed_id: kg_per_head * days
            for feed_id, kg_per_head in per_head["feed_kg_per_head"].items()
        },
    }


def reverse_from_budget(animal_id, weight_kg, output_per_head, regime, days, budget_kg_by_feed):
    """По имеющемуся объёму корма (кг по видам) — сколько голов можно
    прокормить указанное число дней. Считаем по суммарной энергетической
    ценности (ЭКЕ) имеющегося корма относительно суточной потребности одной
    головы — не по отдельным видам корма (реальный рацион можно скорректировать
    вручную под то, что реально есть)."""
    per_head = compute_ration_per_head(animal_id, weight_kg, output_per_head, regime)
    total_efu_available = sum(
        qty_kg * FEED_TYPES[feed_id]["efu_per_kg"]
        for feed_id, qty_kg in budget_kg_by_feed.items()
        if feed_id in FEED_TYPES
    )
    efu_per_head_period = per_head["total_efu_per_head"] * days
    max_count = math.floor(total_efu_available / efu_per_head_period) if efu_per_head_period > 0 else 0

    return {
        "animal_id": animal_id,
        "days": days,
        "per_head": per_head,
        "total_efu_available": total_efu_available,
        "efu_per_head_period": efu_per_head_period,
        "max_count": max_count,
        "forward_check": forward(animal_id, weight_kg, output_per_head, regime, max_count, days) if max_count else None,
    }


def reverse_from_target_output(animal_id, weight_kg, regime, days, target_total_output, output_per_head):
    """По желаемому суммарному результату (например, всего литров молока за
    период) — сколько голов нужно держать и сколько для этого нужно корма."""
    if output_per_head <= 0:
        raise ValueError("Продуктивность на голову должна быть больше нуля.")
    required_count = math.ceil(target_total_output / (output_per_head * days))
    result = forward(animal_id, weight_kg, output_per_head, regime, required_count, days)
    result["target_total_output"] = target_total_output
    result["required_count"] = required_count
    return result
