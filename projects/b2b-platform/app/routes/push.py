"""Регистрация push-токена мобильного приложения (модуль 7) — см. app/push.py."""
from flask import Blueprint, jsonify, request
from flask_login import current_user

from app import db
from app.decorators import paywall_required
from app.models import PushDeviceToken

bp = Blueprint("push", __name__)


@bp.route("/push/register", methods=["POST"])
@paywall_required
def register():
    data = request.get_json(silent=True) or {}
    token = (data.get("token") or "").strip()
    platform = (data.get("platform") or "android").strip()[:20]
    if not token:
        return jsonify({"ok": False, "error": "token required"}), 400

    existing = PushDeviceToken.query.filter_by(token=token).first()
    if existing is not None:
        existing.user_id = current_user.id
        existing.platform = platform
    else:
        db.session.add(PushDeviceToken(user_id=current_user.id, token=token, platform=platform))
    db.session.commit()
    return jsonify({"ok": True})


@bp.route("/push/unregister", methods=["POST"])
@paywall_required
def unregister():
    data = request.get_json(silent=True) or {}
    token = (data.get("token") or "").strip()
    if token:
        PushDeviceToken.query.filter_by(token=token, user_id=current_user.id).delete()
        db.session.commit()
    return jsonify({"ok": True})
