# -*- coding: utf-8 -*-
"""
Агро-калькулятор: корм для животных + посев/удобрения.
Роуты:
  GET  /                       -> интерфейс
  GET  /api/data                -> справочники (животные/культуры/корма/удобрения) для UI
  POST /api/feed/calculate      -> расчёт кормления (прямой/обратный), JSON
  POST /api/feed/report         -> .docx отчёт по кормлению
  POST /api/crop/calculate      -> расчёт посева (прямой/обратный + экономика), JSON
  POST /api/crop/report         -> .docx отчёт по посеву
Без БД и аккаунтов — чистый калькулятор, как balka/rashet-ferm.
"""
import io
import os
import tempfile
import traceback
from datetime import date, datetime

from flask import Flask, request, jsonify, send_file, render_template

import feed_calc
import crop_calc
import report
from norms import ANIMALS, CROPS, FEED_TYPES, FERTILIZERS, FEEDING_REGIMES

app = Flask(__name__)


def _parse_date(s):
    if not s:
        return None
    return datetime.strptime(s, "%Y-%m-%d").date()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/data")
def api_data():
    return jsonify({
        "animals": {k: {"label": v["label"], "weight_default": v["weight_default"],
                         "weight_min": v["weight_min"], "weight_max": v["weight_max"],
                         "production": v["production"]}
                    for k, v in ANIMALS.items()},
        "crops": {k: {"label": v["label"], "seeding_rate_kg_ha": v["seeding_rate_kg_ha"],
                      "yield_t_ha": v["yield_t_ha"], "growth_days": v["growth_days"]}
                  for k, v in CROPS.items()},
        "feed_types": FEED_TYPES,
        "fertilizers": FERTILIZERS,
        "regimes": FEEDING_REGIMES,
    })


def _run_feed_calc(data):
    mode = data.get("mode", "forward")
    animal_id = data["animal_id"]
    weight = float(data["weight"])
    regime = data.get("regime", "winter")
    days = int(data["days"])
    output_per_head = float(data.get("output_per_head", ANIMALS[animal_id]["production"]["default"]))

    if mode == "forward":
        count = int(data["count"])
        return feed_calc.forward(animal_id, weight, output_per_head, regime, count, days)
    elif mode == "reverse_budget":
        budget = {k: float(v) for k, v in data.get("budget_kg_by_feed", {}).items() if float(v or 0) > 0}
        return feed_calc.reverse_from_budget(animal_id, weight, output_per_head, regime, days, budget)
    elif mode == "reverse_target":
        target = float(data["target_total_output"])
        return feed_calc.reverse_from_target_output(animal_id, weight, regime, days, target, output_per_head)
    else:
        raise ValueError("Неизвестный режим расчёта: " + str(mode))


def _run_feed_econ(data, mode, result):
    """Экономика необязательна: считаем, только если дали хоть одну цену.
    Для reverse_budget считаем по факту прокормленного поголовья
    (result['forward_check']), а не по абстрактному бюджету корма."""
    feed_prices = {k: float(v or 0) for k, v in (data.get("feed_prices") or {}).items()}
    output_price = float(data.get("output_price") or 0)
    if not any(feed_prices.values()) and not output_price:
        return None
    basis = result.get("forward_check") if mode == "reverse_budget" else result
    if not basis:
        return None
    return feed_calc.economics(basis, feed_prices, output_price)


@app.route("/api/feed/calculate", methods=["POST"])
def api_feed_calculate():
    data = request.get_json(force=True)
    try:
        mode = data.get("mode", "forward")
        result = _run_feed_calc(data)
        econ = _run_feed_econ(data, mode, result)
        return jsonify({"ok": True, "result": result, "econ": econ})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 400


@app.route("/api/feed/report", methods=["POST"])
def api_feed_report():
    data = request.get_json(force=True)
    try:
        mode = data.get("mode", "forward")
        result = _run_feed_calc(data)
        econ = _run_feed_econ(data, mode, result)
        ctx = {"animal_id": data["animal_id"], "result": result, "econ": econ,
               "author": data.get("author", ""), "date": data.get("date", "")}
        with tempfile.TemporaryDirectory() as tmp:
            out_path = os.path.join(tmp, "feed_report.docx")
            report.generate_feed_report(ctx, out_path)
            buf = io.BytesIO()
            with open(out_path, "rb") as fh:
                buf.write(fh.read())
            buf.seek(0)
        return send_file(buf, as_attachment=True, download_name="Расчёт_кормления.docx",
                          mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 400


def _run_crop_calc(data):
    mode = data.get("mode", "forward")
    crop_id = data["crop_id"]
    yield_t_ha = float(data["yield_t_ha"]) if data.get("yield_t_ha") else None
    fertilizer_choice = data.get("fertilizer_choice") or {}
    sowing_date = _parse_date(data.get("sowing_date"))

    if mode == "forward":
        area_ha = float(data["area_ha"])
        result = crop_calc.forward(crop_id, area_ha, yield_t_ha, fertilizer_choice, sowing_date)
    elif mode == "reverse_target":
        target = float(data["target_total_yield_t"])
        result = crop_calc.reverse_from_target_yield(crop_id, target, yield_t_ha, fertilizer_choice, sowing_date)
    else:
        raise ValueError("Неизвестный режим расчёта: " + str(mode))

    econ = None
    prices = data.get("prices")
    if prices and any(float(v or 0) > 0 for v in prices.values() if not isinstance(v, dict)):
        econ = crop_calc.economics(result, prices)
    elif prices and prices.get("fert_price_per_kg"):
        econ = crop_calc.economics(result, prices)

    return result, econ


@app.route("/api/crop/calculate", methods=["POST"])
def api_crop_calculate():
    data = request.get_json(force=True)
    try:
        result, econ = _run_crop_calc(data)
        return jsonify({"ok": True, "result": result, "econ": econ})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 400


@app.route("/api/crop/report", methods=["POST"])
def api_crop_report():
    data = request.get_json(force=True)
    try:
        result, econ = _run_crop_calc(data)
        ctx = {"crop_id": data["crop_id"], "result": result, "econ": econ,
               "author": data.get("author", ""), "date": data.get("date", "")}
        with tempfile.TemporaryDirectory() as tmp:
            out_path = os.path.join(tmp, "crop_report.docx")
            report.generate_crop_report(ctx, out_path)
            buf = io.BytesIO()
            with open(out_path, "rb") as fh:
                buf.write(fh.read())
            buf.seek(0)
        return send_file(buf, as_attachment=True, download_name="Расчёт_посева.docx",
                          mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 400


if __name__ == "__main__":
    app.run(debug=True, port=5060)
