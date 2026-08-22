# -*- coding: utf-8 -*-
"""
Справочные нормы для расчёта кормления животных и посева/удобрения культур.

Все коэффициенты — типовые ориентировочные значения из общепринятых
зоотехнических и агрономических справочников (структура норм кормления по
энергетическим кормовым единицам — ЭКЕ, нормы высева, вынос питательных
веществ с урожаем и т.п.). Реальные хозяйства отличаются по породе/сорту,
зоне, погоде и качеству кормов/почвы, поэтому цифры сделаны видимыми и
редактируемыми прямо в интерфейсе — это не замена агронома/зоотехника для
конкретного хозяйства, а быстрая прикидка "сколько примерно нужно".
"""

# --- Корма: энергетическая ценность (ЭКЕ на 1 кг корма) -------------------
FEED_TYPES = {
    "concentrate": {"label": "Концентраты (зерно/комбикорм)", "efu_per_kg": 1.10},
    "bran":        {"label": "Отруби",                        "efu_per_kg": 0.75},
    "hay":         {"label": "Сено",                           "efu_per_kg": 0.45},
    "haylage":     {"label": "Сенаж",                          "efu_per_kg": 0.34},
    "silage":      {"label": "Силос",                          "efu_per_kg": 0.20},
    "straw":       {"label": "Солома",                         "efu_per_kg": 0.20},
    "roots":       {"label": "Корнеплоды/картофель",           "efu_per_kg": 0.20},
    "green":       {"label": "Зелёная масса/пастбище",         "efu_per_kg": 0.20},
    "mix_feed":    {"label": "Комбикорм (полнорационный)",     "efu_per_kg": 1.15},
}

# --- Животные ---------------------------------------------------------------
# maintenance_efu_per_100kg — ЭКЕ на поддержание жизни на 100 кг живой массы/сутки
# production:
#   unit_label — единица показателя продуктивности
#   efu_per_unit — сколько ЭКЕ нужно сверх поддержания на 1 единицу продукции/сутки
# rations — норма кормления: доля суточной потребности в ЭКЕ, покрываемая
#   каждым видом корма, отдельно для двух режимов (зима/стойловый и
#   лето/пастбищный); доли в каждом режиме должны суммарно давать 1.0.
ANIMALS = {
    "dairy_cow": {
        "label": "Дойная корова",
        "weight_default": 500, "weight_min": 350, "weight_max": 750,
        "maintenance_efu_per_100kg": 0.85,
        "production": {"unit_label": "л молока/сутки (удой)", "efu_per_unit": 0.50, "default": 15},
        "rations": {
            "winter": {"concentrate": 0.30, "hay": 0.20, "haylage": 0.15, "silage": 0.30, "roots": 0.05},
            "summer": {"concentrate": 0.30, "green": 0.65, "mix_feed": 0.05},
        },
    },
    "beef_cattle": {
        "label": "КРС на откорме / молодняк",
        "weight_default": 300, "weight_min": 100, "weight_max": 600,
        "maintenance_efu_per_100kg": 0.80,
        "production": {"unit_label": "г среднесуточного привеса (×100)", "efu_per_unit": 0.45, "default": 8},
        "rations": {
            "winter": {"concentrate": 0.35, "hay": 0.15, "haylage": 0.15, "silage": 0.30, "straw": 0.05},
            "summer": {"concentrate": 0.35, "green": 0.60, "mix_feed": 0.05},
        },
    },
    "sow_pregnant": {
        "label": "Свиноматка супоросная",
        "weight_default": 180, "weight_min": 120, "weight_max": 260,
        "maintenance_efu_per_100kg": 1.10,
        "production": {"unit_label": "голов приплода в ожидании (условно)", "efu_per_unit": 0.10, "default": 10},
        "rations": {
            "winter": {"concentrate": 0.70, "roots": 0.15, "hay": 0.10, "bran": 0.05},
            "summer": {"concentrate": 0.65, "green": 0.25, "bran": 0.10},
        },
    },
    "sow_lactating": {
        "label": "Свиноматка подсосная",
        "weight_default": 200, "weight_min": 140, "weight_max": 280,
        "maintenance_efu_per_100kg": 1.10,
        "production": {"unit_label": "поросят под маткой", "efu_per_unit": 0.60, "default": 10},
        "rations": {
            "winter": {"concentrate": 0.80, "roots": 0.10, "bran": 0.10},
            "summer": {"concentrate": 0.75, "green": 0.15, "bran": 0.10},
        },
    },
    "pig_fattening": {
        "label": "Свинья на откорме",
        "weight_default": 60, "weight_min": 20, "weight_max": 120,
        "maintenance_efu_per_100kg": 1.05,
        "production": {"unit_label": "г среднесуточного привеса (×100)", "efu_per_unit": 0.30, "default": 6},
        "rations": {
            "winter": {"concentrate": 0.85, "roots": 0.10, "bran": 0.05},
            "summer": {"concentrate": 0.80, "green": 0.10, "bran": 0.10},
        },
    },
    "sheep_ewe": {
        "label": "Овцематка (суягная/подсосная)",
        "weight_default": 55, "weight_min": 35, "weight_max": 90,
        "maintenance_efu_per_100kg": 1.00,
        "production": {"unit_label": "ягнят под маткой", "efu_per_unit": 0.35, "default": 1},
        "rations": {
            "winter": {"concentrate": 0.15, "hay": 0.45, "silage": 0.30, "straw": 0.10},
            "summer": {"concentrate": 0.10, "green": 0.90},
        },
    },
    "sheep_fattening": {
        "label": "Овца/молодняк на откорме",
        "weight_default": 35, "weight_min": 15, "weight_max": 70,
        "maintenance_efu_per_100kg": 1.00,
        "production": {"unit_label": "г среднесуточного привеса (×100)", "efu_per_unit": 0.40, "default": 1.5},
        "rations": {
            "winter": {"concentrate": 0.20, "hay": 0.40, "silage": 0.30, "straw": 0.10},
            "summer": {"concentrate": 0.15, "green": 0.85},
        },
    },
    "goat": {
        "label": "Коза (дойная/суягная)",
        "weight_default": 45, "weight_min": 25, "weight_max": 70,
        "maintenance_efu_per_100kg": 1.00,
        "production": {"unit_label": "л молока/сутки", "efu_per_unit": 0.45, "default": 2.5},
        "rations": {
            "winter": {"concentrate": 0.20, "hay": 0.45, "silage": 0.20, "straw": 0.15},
            "summer": {"concentrate": 0.15, "green": 0.85},
        },
    },
    "laying_hen": {
        "label": "Курица-несушка",
        "weight_default": 2, "weight_min": 1.5, "weight_max": 3,
        "maintenance_efu_per_100kg": 3.20,
        "production": {"unit_label": "яиц в месяц на голову (÷30 в сутки)", "efu_per_unit": 0.012, "default": 22},
        "rations": {
            "winter": {"concentrate": 0.55, "mix_feed": 0.35, "roots": 0.10},
            "summer": {"concentrate": 0.50, "mix_feed": 0.30, "green": 0.20},
        },
    },
    "broiler": {
        "label": "Бройлер (откорм)",
        "weight_default": 1.5, "weight_min": 0.1, "weight_max": 2.5,
        "maintenance_efu_per_100kg": 4.00,
        "production": {"unit_label": "г среднесуточного привеса (×10)", "efu_per_unit": 0.20, "default": 5},
        "rations": {
            "winter": {"mix_feed": 0.90, "concentrate": 0.10},
            "summer": {"mix_feed": 0.90, "concentrate": 0.10},
        },
    },
    "rabbit": {
        "label": "Кролик (на откорме/матка)",
        "weight_default": 4, "weight_min": 1, "weight_max": 6,
        "maintenance_efu_per_100kg": 3.00,
        "production": {"unit_label": "г среднесуточного привеса (×10)", "efu_per_unit": 0.15, "default": 3},
        "rations": {
            "winter": {"concentrate": 0.35, "hay": 0.40, "roots": 0.25},
            "summer": {"concentrate": 0.30, "green": 0.70},
        },
    },
}

# --- Культуры (посев) -------------------------------------------------------
# seeding_rate_kg_ha — типовая норма высева, кг/га (для картофеля — семенные
#   клубни, для остальных — семена)
# yield_t_ha — типовая ожидаемая урожайность, т/га (для прикидки площади/сбора)
# removal_kg_per_t — вынос N/P2O5/K2O с урожаем, кг на 1 т основной продукции
#   (с учётом побочной продукции — типовые агрономические ориентиры)
# water_m3_ha — суммарная потребность в поливе за сезон, м³/га (для богары/
#   осадков — ориентир, при поливном земледелии считать как дополнение к
#   осадкам)
# growth_days — (мин, макс) дней от посева до созревания/уборки
# labor_days_ha — типовые трудозатраты, чел.-дней на 1 га за сезон
#   (посев+уход+уборка)
CROPS = {
    "wheat_winter": {
        "label": "Пшеница озимая", "seeding_rate_kg_ha": 220, "yield_t_ha": 4.0,
        "removal_kg_per_t": {"N": 30, "P2O5": 11, "K2O": 20},
        "water_m3_ha": 4000, "growth_days": (270, 320), "labor_days_ha": 2.5,
    },
    "wheat_spring": {
        "label": "Пшеница яровая", "seeding_rate_kg_ha": 200, "yield_t_ha": 3.0,
        "removal_kg_per_t": {"N": 33, "P2O5": 11, "K2O": 22},
        "water_m3_ha": 3500, "growth_days": (85, 110), "labor_days_ha": 2.5,
    },
    "barley": {
        "label": "Ячмень", "seeding_rate_kg_ha": 190, "yield_t_ha": 3.5,
        "removal_kg_per_t": {"N": 27, "P2O5": 11, "K2O": 22},
        "water_m3_ha": 3200, "growth_days": (70, 100), "labor_days_ha": 2.2,
    },
    "oats": {
        "label": "Овёс", "seeding_rate_kg_ha": 180, "yield_t_ha": 3.0,
        "removal_kg_per_t": {"N": 29, "P2O5": 11, "K2O": 25},
        "water_m3_ha": 3300, "growth_days": (80, 110), "labor_days_ha": 2.2,
    },
    "rye": {
        "label": "Рожь озимая", "seeding_rate_kg_ha": 190, "yield_t_ha": 3.2,
        "removal_kg_per_t": {"N": 28, "P2O5": 12, "K2O": 22},
        "water_m3_ha": 3800, "growth_days": (280, 330), "labor_days_ha": 2.3,
    },
    "corn_grain": {
        "label": "Кукуруза на зерно", "seeding_rate_kg_ha": 22, "yield_t_ha": 6.0,
        "removal_kg_per_t": {"N": 24, "P2O5": 9, "K2O": 25},
        "water_m3_ha": 5500, "growth_days": (110, 140), "labor_days_ha": 3.0,
    },
    "corn_silage": {
        "label": "Кукуруза на силос", "seeding_rate_kg_ha": 25, "yield_t_ha": 35.0,
        "removal_kg_per_t": {"N": 4, "P2O5": 1.5, "K2O": 4.5},
        "water_m3_ha": 5000, "growth_days": (90, 120), "labor_days_ha": 2.8,
    },
    "sunflower": {
        "label": "Подсолнечник", "seeding_rate_kg_ha": 5, "yield_t_ha": 2.0,
        "removal_kg_per_t": {"N": 50, "P2O5": 22, "K2O": 150},
        "water_m3_ha": 4500, "growth_days": (100, 130), "labor_days_ha": 2.6,
    },
    "soybean": {
        "label": "Соя", "seeding_rate_kg_ha": 90, "yield_t_ha": 2.0,
        "removal_kg_per_t": {"N": 70, "P2O5": 15, "K2O": 25},
        "water_m3_ha": 4200, "growth_days": (100, 140), "labor_days_ha": 2.7,
    },
    "rapeseed": {
        "label": "Рапс", "seeding_rate_kg_ha": 5, "yield_t_ha": 2.2,
        "removal_kg_per_t": {"N": 55, "P2O5": 25, "K2O": 40},
        "water_m3_ha": 3800, "growth_days": (280, 330), "labor_days_ha": 2.6,
    },
    "potato": {
        "label": "Картофель", "seeding_rate_kg_ha": 2800, "yield_t_ha": 25.0,
        "removal_kg_per_t": {"N": 5, "P2O5": 1.8, "K2O": 7},
        "water_m3_ha": 4500, "growth_days": (70, 110), "labor_days_ha": 12.0,
    },
    "sugar_beet": {
        "label": "Сахарная свёкла", "seeding_rate_kg_ha": 6, "yield_t_ha": 45.0,
        "removal_kg_per_t": {"N": 4.5, "P2O5": 1.5, "K2O": 6.5},
        "water_m3_ha": 5500, "growth_days": (150, 180), "labor_days_ha": 8.0,
    },
}

# --- Удобрения (для перевода кг д.в. в кг товарного продукта) --------------
FERTILIZERS = {
    "N": [
        {"id": "urea", "label": "Карбамид (мочевина, 46% N)", "pct": 0.46},
        {"id": "ammonium_nitrate", "label": "Аммиачная селитра (34% N)", "pct": 0.34},
    ],
    "P2O5": [
        {"id": "superphosphate_double", "label": "Суперфосфат двойной (46% P₂O₅)", "pct": 0.46},
        {"id": "superphosphate_simple", "label": "Суперфосфат простой (19% P₂O₅)", "pct": 0.19},
    ],
    "K2O": [
        {"id": "potassium_chloride", "label": "Хлористый калий (60% K₂О)", "pct": 0.60},
        {"id": "potassium_sulfate", "label": "Сульфат калия (50% K₂О)", "pct": 0.50},
    ],
}

FEEDING_REGIMES = {
    "winter": "Стойловый (зима)",
    "summer": "Пастбищный/смешанный (лето)",
}
