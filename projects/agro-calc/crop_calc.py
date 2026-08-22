# -*- coding: utf-8 -*-
"""Расчёт посева: прямой (по площади -> сколько семян/удобрений/воды нужно
и какой ожидается сбор) и обратный (по желаемому сбору -> сколько нужно
площади), плюс календарь созревания, трудозатраты и экономика."""
import math
from datetime import date, timedelta

from norms import CROPS, FERTILIZERS


def _fertilizer_products(nutrient_kg, fertilizer_choice):
    """nutrient_kg: {"N": .., "P2O5": .., "K2O": ..} -> кг товарного удобрения
    по выбранным пользователем маркам (fertilizer_choice: {"N": fert_id, ...})."""
    products = {}
    for nutrient, kg in nutrient_kg.items():
        fert_id = fertilizer_choice.get(nutrient)
        options = FERTILIZERS.get(nutrient, [])
        fert = next((f for f in options if f["id"] == fert_id), options[0] if options else None)
        if fert and kg > 0:
            products[nutrient] = {
                "fertilizer_label": fert["label"],
                "product_kg": kg / fert["pct"],
            }
    return products


def forward(crop_id, area_ha, yield_t_ha=None, fertilizer_choice=None, sowing_date=None):
    crop = CROPS[crop_id]
    yield_t_ha = yield_t_ha if yield_t_ha else crop["yield_t_ha"]
    fertilizer_choice = fertilizer_choice or {}

    seed_kg = crop["seeding_rate_kg_ha"] * area_ha
    total_yield_t = yield_t_ha * area_ha
    water_m3 = crop["water_m3_ha"] * area_ha
    labor_days = crop["labor_days_ha"] * area_ha

    nutrient_kg = {
        nutrient: rate * total_yield_t
        for nutrient, rate in crop["removal_kg_per_t"].items()
    }
    fertilizer_products = _fertilizer_products(nutrient_kg, fertilizer_choice)

    harvest_range = None
    if sowing_date:
        d_min, d_max = crop["growth_days"]
        harvest_range = (
            (sowing_date + timedelta(days=d_min)).isoformat(),
            (sowing_date + timedelta(days=d_max)).isoformat(),
        )

    return {
        "crop_id": crop_id,
        "area_ha": area_ha,
        "yield_t_ha": yield_t_ha,
        "total_yield_t": total_yield_t,
        "seed_kg": seed_kg,
        "water_m3": water_m3,
        "labor_days": labor_days,
        "nutrient_kg": nutrient_kg,
        "fertilizer_products": fertilizer_products,
        "growth_days": crop["growth_days"],
        "sowing_date": sowing_date.isoformat() if sowing_date else None,
        "harvest_range": harvest_range,
    }


def reverse_from_target_yield(crop_id, target_total_yield_t, yield_t_ha=None, fertilizer_choice=None, sowing_date=None):
    crop = CROPS[crop_id]
    yield_t_ha = yield_t_ha if yield_t_ha else crop["yield_t_ha"]
    if yield_t_ha <= 0:
        raise ValueError("Урожайность на га должна быть больше нуля.")
    required_area_ha = target_total_yield_t / yield_t_ha
    result = forward(crop_id, required_area_ha, yield_t_ha, fertilizer_choice, sowing_date)
    result["target_total_yield_t"] = target_total_yield_t
    result["required_area_ha"] = required_area_ha
    return result


def economics(forward_result, prices):
    """prices: {price_per_t, seed_price_per_kg, fert_price_per_kg (общий,
    опционально по нутриенту {"N":.., "P2O5":.., "K2O":..}), water_price_per_m3,
    daily_wage} — любые можно не указывать (0/None), тогда эта статья не
    учитывается."""
    revenue = forward_result["total_yield_t"] * (prices.get("price_per_t") or 0)

    seed_cost = forward_result["seed_kg"] * (prices.get("seed_price_per_kg") or 0)
    water_cost = forward_result["water_m3"] * (prices.get("water_price_per_m3") or 0)
    labor_cost = forward_result["labor_days"] * (prices.get("daily_wage") or 0)

    fert_prices = prices.get("fert_price_per_kg") or {}
    fert_cost = 0.0
    fert_cost_breakdown = {}
    for nutrient, info in forward_result["fertilizer_products"].items():
        price = fert_prices.get(nutrient) or 0
        cost = info["product_kg"] * price
        fert_cost += cost
        fert_cost_breakdown[nutrient] = cost

    total_cost = seed_cost + water_cost + labor_cost + fert_cost
    profit = revenue - total_cost

    return {
        "revenue": revenue,
        "seed_cost": seed_cost,
        "water_cost": water_cost,
        "labor_cost": labor_cost,
        "fert_cost": fert_cost,
        "fert_cost_breakdown": fert_cost_breakdown,
        "total_cost": total_cost,
        "profit": profit,
    }
