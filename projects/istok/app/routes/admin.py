"""Панель модерации предложенных правок (/admin)."""
import hmac
from datetime import datetime
from functools import wraps

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from app import db
from app.models import EditSuggestion

bp = Blueprint("admin", __name__, template_folder="../templates/admin")


@bp.route("/")
def index():
    if session.get("is_admin"):
        return redirect(url_for("admin.suggestions"))
    return redirect(url_for("admin.login"))


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("admin.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        password = request.form.get("password", "")
        expected = current_app.config["ADMIN_PASSWORD"]
        if hmac.compare_digest(password, expected):
            session["is_admin"] = True
            flash("Вы вошли в панель модерации.", "success")
            return redirect(request.args.get("next") or url_for("admin.suggestions"))
        flash("Неверный пароль.", "error")
    return render_template("admin/login.html")


@bp.route("/logout")
def logout():
    session.pop("is_admin", None)
    flash("Вы вышли из панели модерации.", "info")
    return redirect(url_for("admin.login"))


@bp.route("/suggestions")
@login_required
def suggestions():
    status = request.args.get("status", EditSuggestion.STATUS_PENDING)
    query = EditSuggestion.query
    if status in (EditSuggestion.STATUS_PENDING, EditSuggestion.STATUS_APPROVED, EditSuggestion.STATUS_REJECTED):
        query = query.filter_by(status=status)
    items = query.order_by(EditSuggestion.created_at.desc()).all()
    pending_count = EditSuggestion.query.filter_by(status=EditSuggestion.STATUS_PENDING).count()
    return render_template(
        "admin/suggestions.html",
        items=items,
        active_status=status,
        pending_count=pending_count,
    )


@bp.route("/suggestions/<int:suggestion_id>/approve", methods=["POST"])
@login_required
def approve(suggestion_id):
    suggestion = EditSuggestion.query.get_or_404(suggestion_id)
    if suggestion.status == EditSuggestion.STATUS_PENDING:
        setattr(suggestion.source, suggestion.field_name, suggestion.proposed_value)
        suggestion.status = EditSuggestion.STATUS_APPROVED
        suggestion.reviewed_at = datetime.utcnow()
        db.session.commit()
        flash(f"Правка применена к «{suggestion.source.name}».", "success")
    return redirect(url_for("admin.suggestions"))


@bp.route("/suggestions/<int:suggestion_id>/reject", methods=["POST"])
@login_required
def reject(suggestion_id):
    suggestion = EditSuggestion.query.get_or_404(suggestion_id)
    if suggestion.status == EditSuggestion.STATUS_PENDING:
        suggestion.status = EditSuggestion.STATUS_REJECTED
        suggestion.reviewed_at = datetime.utcnow()
        db.session.commit()
        flash("Предложение отклонено.", "info")
    return redirect(url_for("admin.suggestions"))
