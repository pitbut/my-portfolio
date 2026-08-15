"""Переписка игрока с администратором (поддержка), включая фото."""
from flask import Blueprint, abort, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required

from app import db
from app.models import SupportMessage
from app.uploads import save_support_photo, support_photo_path

bp = Blueprint("support", __name__)


@bp.route("/")
@login_required
def index():
    messages = (
        SupportMessage.query.filter_by(user_id=current_user.id)
        .order_by(SupportMessage.created_at.asc())
        .all()
    )
    return render_template("support/index.html", messages=messages)


@bp.route("/send", methods=["POST"])
@login_required
def send():
    body = (request.form.get("body") or "").strip()
    photo = request.files.get("photo")

    try:
        photo_filename = save_support_photo(photo)
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("support.index"))

    if not body and not photo_filename:
        flash("Напишите сообщение или приложите фото.", "error")
        return redirect(url_for("support.index"))

    message = SupportMessage(
        user_id=current_user.id,
        sender_is_admin=False,
        body=body or None,
        photo_filename=photo_filename,
    )
    db.session.add(message)
    db.session.commit()

    flash("Сообщение отправлено.", "success")
    return redirect(url_for("support.index"))


@bp.route("/photo/<int:message_id>")
@login_required
def photo(message_id):
    message = SupportMessage.query.get_or_404(message_id)
    if message.user_id != current_user.id and not current_user.is_admin:
        abort(403)
    if not message.photo_filename:
        abort(404)
    return send_file(support_photo_path(message.photo_filename))
