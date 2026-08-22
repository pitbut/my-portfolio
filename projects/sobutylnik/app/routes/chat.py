"""Комната беседы с ИИ-собеседником: текст/голос (распознавание и озвучка —
на клиенте, см. static/js/voice.js), действия тост/шутка/чокнуться/музыка,
фото обстановки."""
from datetime import datetime

from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.models import Conversation, Message, get_settings
from app.prompts import SCENE_PHOTO_PROMPT, action_request_text, build_companion_system_prompt
from app.providers import AIProviderError, get_provider
from app.uploads import MAX_UPLOAD_SIZE, upload_bytes

bp = Blueprint("chat", __name__)

MAX_HISTORY_MESSAGES = 20  # сколько последних реплик передаём модели как контекст


def _active_conversation():
    conv = (
        Conversation.query.filter_by(user_id=current_user.id, ended_at=None)
        .order_by(Conversation.started_at.desc())
        .first()
    )
    if conv is None or conv.companion_key != current_user.companion_key:
        if conv is not None:
            conv.ended_at = datetime.utcnow()
        conv = Conversation(user_id=current_user.id, companion_key=current_user.companion_key)
        db.session.add(conv)
        db.session.commit()
    return conv


def _history_for_ai(conversation):
    history = []
    for m in conversation.messages[-MAX_HISTORY_MESSAGES:]:
        role = "user" if m.sender == Message.SENDER_USER else "assistant"
        history.append({"role": role, "content": m.content})
    return history


def _limit_status():
    settings = get_settings()
    if not settings.limits_enabled:
        return settings, None
    limit = current_user.effective_limit(settings.default_message_limit)
    return settings, limit


def _check_limit():
    settings, limit = _limit_status()
    if limit is not None and current_user.messages_used >= limit:
        return True
    return False


@bp.route("/")
@login_required
def room():
    if not current_user.companion_key:
        flash("Сначала выберите собеседника.", "info")
        return redirect(url_for("main.dashboard"))

    conversation = _active_conversation()
    settings, limit = _limit_status()
    return render_template(
        "main/room.html",
        companion=current_user.companion,
        conversation=conversation,
        messages=conversation.messages,
        limit=limit,
        messages_used=current_user.messages_used,
        limit_reached=_check_limit(),
    )


@bp.route("/message", methods=["POST"])
@login_required
def send_message():
    if _check_limit():
        return jsonify({"limit_reached": True}), 200

    text = (request.json or {}).get("text", "").strip()
    action = (request.json or {}).get("action")  # toast|joke|music|cheers, опционально
    if not text and not action:
        return jsonify({"error": "empty"}), 400

    conversation = _active_conversation()
    user_text = text or action_request_text(action)

    system_prompt = build_companion_system_prompt(current_user.companion, current_user.name)
    history = _history_for_ai(conversation)

    try:
        provider = get_provider()
        reply, _usage = provider.send_message(system_prompt, history, user_text, max_tokens=500)
    except AIProviderError as exc:
        return jsonify({"error": str(exc)}), 503

    db.session.add(Message(
        conversation_id=conversation.id, sender=Message.SENDER_USER,
        kind=action or Message.KIND_TEXT, content=user_text,
    ))
    db.session.add(Message(
        conversation_id=conversation.id, sender=Message.SENDER_COMPANION,
        kind=action or Message.KIND_TEXT, content=reply,
    ))
    current_user.messages_used += 1
    db.session.commit()

    return jsonify({"reply": reply, "messages_used": current_user.messages_used})


@bp.route("/scene", methods=["POST"])
@login_required
def scene_photo():
    """Пользователь показывает обстановку (фото со своей камеры/галереи) —
    ИИ анализирует кадр через vision и реагирует в своём стиле."""
    if _check_limit():
        return jsonify({"limit_reached": True}), 200

    file = request.files.get("photo")
    if file is None or not file.filename:
        return jsonify({"error": "no_file"}), 400

    data = file.read(MAX_UPLOAD_SIZE + 1)
    if len(data) > MAX_UPLOAD_SIZE:
        return jsonify({"error": "too_large"}), 400
    mimetype = file.mimetype or "image/jpeg"

    conversation = _active_conversation()
    system_prompt = build_companion_system_prompt(current_user.companion, current_user.name)
    history = _history_for_ai(conversation)

    try:
        provider = get_provider()
        content = provider.build_image_content(SCENE_PHOTO_PROMPT, data, mimetype)
        reply, _usage = provider.send_message(system_prompt, history, content, max_tokens=400)
    except AIProviderError as exc:
        return jsonify({"error": str(exc)}), 503

    image_url = upload_bytes(data, file.filename, mimetype)

    db.session.add(Message(
        conversation_id=conversation.id, sender=Message.SENDER_USER,
        kind=Message.KIND_TEXT, content="[показал(а) фото обстановки]", image_url=image_url,
    ))
    db.session.add(Message(
        conversation_id=conversation.id, sender=Message.SENDER_COMPANION,
        kind=Message.KIND_TEXT, content=reply,
    ))
    current_user.messages_used += 1
    db.session.commit()

    return jsonify({"reply": reply, "image_url": image_url, "messages_used": current_user.messages_used})


@bp.route("/end", methods=["POST"])
@login_required
def end_conversation():
    conversation = _active_conversation()
    conversation.ended_at = datetime.utcnow()
    db.session.commit()
    flash("Беседа завершена. До встречи!", "info")
    return redirect(url_for("main.dashboard"))
