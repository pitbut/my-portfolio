"""Чат техподдержки пользователь↔админ: вопросы про оплату/доступ, с
возможностью прикрепить файл или фото."""
from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.models import SupportMessage
from app.uploads import MAX_UPLOAD_SIZE, upload_bytes

bp = Blueprint("support", __name__)


@bp.route("/")
@login_required
def inbox():
    messages = (
        SupportMessage.query.filter_by(user_id=current_user.id)
        .order_by(SupportMessage.created_at)
        .all()
    )
    for m in messages:
        if m.sender == SupportMessage.SENDER_ADMIN and not m.read_by_user:
            m.read_by_user = True
    db.session.commit()
    return render_template("support/inbox.html", messages=messages)


@bp.route("/send", methods=["POST"])
@login_required
def send():
    body = (request.form.get("body") or "").strip()
    file = request.files.get("attachment")

    attachment_url = None
    attachment_name = None
    if file is not None and file.filename:
        data = file.read(MAX_UPLOAD_SIZE + 1)
        if len(data) > MAX_UPLOAD_SIZE:
            flash("Файл слишком большой (максимум 10 МБ).", "error")
            return redirect(url_for("support.inbox"))
        attachment_url = upload_bytes(data, file.filename, file.mimetype or "application/octet-stream")
        attachment_name = file.filename
        if attachment_url is None:
            flash("Не удалось загрузить файл, но сообщение будет отправлено.", "info")

    if not body and not attachment_url:
        flash("Напишите сообщение или приложите файл.", "error")
        return redirect(url_for("support.inbox"))

    db.session.add(SupportMessage(
        user_id=current_user.id, sender=SupportMessage.SENDER_USER,
        body=body or None, attachment_url=attachment_url, attachment_name=attachment_name,
    ))
    db.session.commit()
    flash("Сообщение отправлено в поддержку.", "success")
    return redirect(url_for("support.inbox"))
