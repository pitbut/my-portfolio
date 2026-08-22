"""Гостевая демо-беседа на главной (реклама до регистрации), личный
кабинет и выбор собеседника."""
from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required

from app import db
from app.companions import COMPANION_CHOICES, get_companion
from app.models import get_settings
from app.prompts import GUEST_DEMO_SYSTEM_PROMPT
from app.providers import AIProviderError, get_provider

bp = Blueprint("main", __name__)

DEMO_HISTORY_KEY = "demo_history"
DEMO_TURNS_KEY = "demo_turns"


@bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    max_turns = current_app.config.get("GUEST_DEMO_TURNS", 4)
    turns_used = session.get(DEMO_TURNS_KEY, 0)
    return render_template(
        "main/index.html",
        companions=COMPANION_CHOICES,
        max_turns=max_turns,
        turns_left=max(max_turns - turns_used, 0),
    )


@bp.route("/demo-reply", methods=["POST"])
def demo_reply():
    """Короткая беседа-реклама без регистрации: несколько реплик с общим
    (не выбираемым) собеседником, дальше — призыв зарегистрироваться. Не
    сохраняется в БД, история живёт только в сессии гостя."""
    if current_user.is_authenticated:
        return jsonify({"error": "already_registered"}), 400

    max_turns = current_app.config.get("GUEST_DEMO_TURNS", 4)
    turns_used = session.get(DEMO_TURNS_KEY, 0)
    if turns_used >= max_turns:
        return jsonify({"limit_reached": True}), 200

    text = (request.json or {}).get("message", "").strip()
    if not text:
        return jsonify({"error": "empty"}), 400

    history = session.get(DEMO_HISTORY_KEY, [])

    try:
        provider = get_provider()
        reply, _usage = provider.send_message(
            GUEST_DEMO_SYSTEM_PROMPT, history, text, max_tokens=300
        )
    except AIProviderError as exc:
        return jsonify({"error": str(exc)}), 503

    history = history + [{"role": "user", "content": text}, {"role": "assistant", "content": reply}]
    session[DEMO_HISTORY_KEY] = history[-8:]  # держим только хвост — гостевая демка короткая
    turns_used += 1
    session[DEMO_TURNS_KEY] = turns_used

    return jsonify({
        "reply": reply,
        "turns_left": max(max_turns - turns_used, 0),
        "limit_reached": turns_used >= max_turns,
    })


@bp.route("/dashboard")
@login_required
def dashboard():
    return render_template("main/dashboard.html", companions=COMPANION_CHOICES)


@bp.route("/companion/select", methods=["POST"])
@login_required
def select_companion():
    key = request.form.get("companion_key")
    if key not in {c["key"] for c in COMPANION_CHOICES}:
        flash("Выберите собеседника из списка.", "error")
        return redirect(url_for("main.dashboard"))
    current_user.companion_key = key
    db.session.commit()
    return redirect(url_for("chat.room"))


@bp.route("/companion/voice", methods=["POST"])
@login_required
def set_voice():
    """Голос выбирается на клиенте из списка, который отдаёт браузер
    (Web Speech API) — сюда просто сохраняется выбранное имя голоса."""
    voice_name = (request.json or {}).get("voice_name", "").strip()
    current_user.voice_name = voice_name or None
    db.session.commit()
    return jsonify({"ok": True})
