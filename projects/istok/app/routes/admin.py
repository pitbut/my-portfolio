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
from app.models import ContactMessage, EditSuggestion, Equipment, Review, Supplier, WaterBrand
from app.routes.reviews import REVIEW_TARGETS

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


@bp.route("/suppliers")
@login_required
def suppliers():
    status = request.args.get("status", "unverified")
    query = Supplier.query
    if status == "unverified":
        query = query.filter_by(verified=False)
    elif status == "verified":
        query = query.filter_by(verified=True)
    items = query.order_by(Supplier.created_at.desc()).all()
    unverified_count = Supplier.query.filter_by(verified=False).count()
    return render_template(
        "admin/suppliers.html",
        items=items,
        active_status=status,
        unverified_count=unverified_count,
    )


@bp.route("/suppliers/<int:supplier_id>/verify", methods=["POST"])
@login_required
def verify_supplier(supplier_id):
    supplier = Supplier.query.get_or_404(supplier_id)
    supplier.verified = True
    db.session.commit()
    flash(f"«{supplier.name}» отмечена как проверенная.", "success")
    return redirect(url_for("admin.suppliers"))


@bp.route("/suppliers/<int:supplier_id>/unverify", methods=["POST"])
@login_required
def unverify_supplier(supplier_id):
    supplier = Supplier.query.get_or_404(supplier_id)
    supplier.verified = False
    db.session.commit()
    flash(f"«{supplier.name}» снова помечена как непроверенная.", "info")
    return redirect(url_for("admin.suppliers"))


@bp.route("/suppliers/<int:supplier_id>/delete", methods=["POST"])
@login_required
def delete_supplier(supplier_id):
    supplier = Supplier.query.get_or_404(supplier_id)
    db.session.delete(supplier)
    db.session.commit()
    flash("Точка продажи удалена.", "info")
    return redirect(url_for("admin.suppliers"))


@bp.route("/equipment")
@login_required
def equipment():
    status = request.args.get("status", "unverified")
    query = Equipment.query
    if status == "unverified":
        query = query.filter_by(verified=False)
    elif status == "verified":
        query = query.filter_by(verified=True)
    items = query.order_by(Equipment.created_at.desc()).all()
    unverified_count = Equipment.query.filter_by(verified=False).count()
    return render_template(
        "admin/equipment.html",
        items=items,
        active_status=status,
        unverified_count=unverified_count,
    )


@bp.route("/equipment/<int:equipment_id>/verify", methods=["POST"])
@login_required
def verify_equipment(equipment_id):
    item = Equipment.query.get_or_404(equipment_id)
    item.verified = True
    db.session.commit()
    flash(f"«{item.name}» отмечено как проверенное.", "success")
    return redirect(url_for("admin.equipment"))


@bp.route("/equipment/<int:equipment_id>/unverify", methods=["POST"])
@login_required
def unverify_equipment(equipment_id):
    item = Equipment.query.get_or_404(equipment_id)
    item.verified = False
    db.session.commit()
    flash(f"«{item.name}» снова помечено как непроверенное.", "info")
    return redirect(url_for("admin.equipment"))


@bp.route("/equipment/<int:equipment_id>/delete", methods=["POST"])
@login_required
def delete_equipment(equipment_id):
    item = Equipment.query.get_or_404(equipment_id)
    db.session.delete(item)
    db.session.commit()
    flash("Оборудование удалено.", "info")
    return redirect(url_for("admin.equipment"))


@bp.route("/water-brands")
@login_required
def water_brands():
    status = request.args.get("status", "unverified")
    query = WaterBrand.query
    if status == "unverified":
        query = query.filter_by(verified=False)
    elif status == "verified":
        query = query.filter_by(verified=True)
    items = query.order_by(WaterBrand.created_at.desc()).all()
    unverified_count = WaterBrand.query.filter_by(verified=False).count()
    return render_template(
        "admin/water_brands.html",
        items=items,
        active_status=status,
        unverified_count=unverified_count,
    )


@bp.route("/water-brands/<int:brand_id>/verify", methods=["POST"])
@login_required
def verify_water_brand(brand_id):
    brand = WaterBrand.query.get_or_404(brand_id)
    brand.verified = True
    db.session.commit()
    flash(f"«{brand.name}» отмечена как проверенная.", "success")
    return redirect(url_for("admin.water_brands"))


@bp.route("/water-brands/<int:brand_id>/unverify", methods=["POST"])
@login_required
def unverify_water_brand(brand_id):
    brand = WaterBrand.query.get_or_404(brand_id)
    brand.verified = False
    db.session.commit()
    flash(f"«{brand.name}» снова помечена как непроверенная.", "info")
    return redirect(url_for("admin.water_brands"))


@bp.route("/water-brands/<int:brand_id>/delete", methods=["POST"])
@login_required
def delete_water_brand(brand_id):
    brand = WaterBrand.query.get_or_404(brand_id)
    db.session.delete(brand)
    db.session.commit()
    flash("Марка воды удалена.", "info")
    return redirect(url_for("admin.water_brands"))


@bp.route("/reviews")
@login_required
def reviews():
    items = Review.query.order_by(Review.created_at.desc()).all()
    enriched = []
    for r in items:
        target_info = REVIEW_TARGETS.get(r.target_type)
        target = db.session.get(target_info["model"], r.target_id) if target_info else None
        target_url = url_for(target_info["endpoint"], slug=target.slug) if target_info and target else None
        target_label = getattr(target, "name", None) or getattr(target, "title", None) or r.target_type
        enriched.append(
            {"review": r, "target": target, "target_url": target_url, "target_label": target_label}
        )
    return render_template("admin/reviews.html", items=enriched, total_count=len(items))


@bp.route("/reviews/<int:review_id>/delete", methods=["POST"])
@login_required
def delete_review(review_id):
    review = Review.query.get_or_404(review_id)
    db.session.delete(review)
    db.session.commit()
    flash("Отзыв удалён.", "info")
    return redirect(url_for("admin.reviews"))


@bp.route("/messages")
@login_required
def messages():
    items = ContactMessage.query.order_by(ContactMessage.created_at.desc()).all()
    unread_count = ContactMessage.query.filter_by(is_read=False).count()
    unread_ids = [m.id for m in items if not m.is_read]
    for message in items:
        message.is_read = True
    if unread_ids:
        db.session.commit()
    return render_template("admin/messages.html", items=items, unread_count=unread_count)
