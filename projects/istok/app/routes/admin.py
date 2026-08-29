"""Панель модерации предложенных правок (/admin)."""
import hmac
from datetime import datetime
from functools import wraps

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from app import db, telegram_bot
from app.book_files import upload_book_files
from app.models import (
    Article,
    Banner,
    Book,
    BookFile,
    ContactMessage,
    DeliveryService,
    EditSuggestion,
    Equipment,
    Experiment,
    Message,
    Review,
    SacredSource,
    SiteStat,
    Supplier,
    User,
    WaterBrand,
)
from app.photos import upload_photo
from app.routes.reviews import REVIEW_TARGETS
from app.text_choices import match_existing

BANNER_SLOTS = (1, 2, 3)

bp = Blueprint("admin", __name__, template_folder="../templates/admin")


@bp.context_processor
def inject_total_views():
    stat = SiteStat.query.get(1)
    return {"total_views": stat.total_views if stat else 0}

# Реестр всех типов пользовательского контента — используется страницей
# пользователя (/admin/users/<id>) и общими роутами
# редактирования/удаления (/admin/content/<type>/<id>/...), чтобы не
# писать отдельные edit/delete-роуты на каждый из 8 разделов сайта.
CONTENT_TYPES = {
    "water_brand": {
        "model": WaterBrand, "label": "Марка воды", "name_field": "name",
        "view_endpoint": "catalog.detail",
        "fields": [
            ("name", "Название", "text"), ("water_type", "Тип воды", "text"),
            ("mineralization_mg_l", "Минерализация, мг/л", "number"),
            ("volume_l", "Объём, л", "number"), ("price", "Цена", "number"),
            ("currency", "Валюта", "text"), ("country", "Страна", "text"),
            ("origin", "Происхождение", "text"), ("description", "Описание", "textarea"),
        ],
    },
    "equipment": {
        "model": Equipment, "label": "Оборудование", "name_field": "name",
        "view_endpoint": "main.equipment_detail",
        "fields": [
            ("name", "Название", "text"), ("category", "Категория", "text"),
            ("description", "Описание", "textarea"), ("manufacturer", "Производитель", "text"),
            ("price_rub", "Цена, ₽", "number"),
        ],
    },
    "supplier": {
        "model": Supplier, "label": "Точка продажи", "name_field": "name",
        "view_endpoint": None,
        "fields": [
            ("name", "Название", "text"), ("supplier_type", "Тип", "text"),
            ("address", "Адрес", "text"), ("phone", "Телефон", "text"),
            ("website", "Сайт", "text"),
        ],
    },
    "book": {
        "model": Book, "label": "Книга", "name_field": "title",
        "view_endpoint": "library.detail",
        "fields": [
            ("title", "Название", "text"), ("author", "Автор", "text"),
            ("year", "Год", "number"), ("genre", "Жанр", "text"),
            ("description", "Описание", "textarea"),
        ],
    },
    "article": {
        "model": Article, "label": "Статья", "name_field": "title",
        "view_endpoint": "articles.detail",
        "fields": [
            ("title", "Заголовок", "text"), ("category", "Рубрика", "text"),
            ("summary", "Краткое содержание", "text"), ("body", "Текст", "textarea"),
        ],
    },
    "sacred_source": {
        "model": SacredSource, "label": "Священный источник", "name_field": "name",
        "view_endpoint": "sacred.detail",
        "fields": [
            ("name", "Название", "text"), ("country", "Страна", "text"),
            ("location", "Местоположение", "text"), ("belief", "Во что верят", "textarea"),
            ("allowed", "Что можно", "textarea"), ("forbidden", "Что нельзя", "textarea"),
            ("description", "Описание", "textarea"), ("comment", "Комментарий редакции", "textarea"),
        ],
    },
    "experiment": {
        "model": Experiment, "label": "Опыт", "name_field": "title",
        "view_endpoint": "main.experiment_detail",
        "fields": [
            ("title", "Название", "text"), ("description", "Описание", "textarea"),
            ("verdict", "Вердикт (наука/миф)", "text"),
        ],
    },
    "delivery_service": {
        "model": DeliveryService, "label": "Служба доставки", "name_field": "name",
        "view_endpoint": "main.delivery_detail",
        "fields": [
            ("name", "Название", "text"), ("coverage", "Зона доставки", "text"),
            ("delivery_time", "Сроки", "text"), ("price_rub", "Цена, ₽", "number"),
            ("phone", "Телефон", "text"), ("website", "Сайт", "text"),
        ],
    },
}


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


@bp.route("/users")
@login_required
def users():
    items = User.query.order_by(User.created_at.desc()).all()
    addition_counts = {
        user.id: sum(
            spec["model"].query.filter_by(added_by_user_id=user.id).count()
            for spec in CONTENT_TYPES.values()
        )
        for user in items
    }
    unread_counts = {
        user.id: Message.query.filter_by(sender_user_id=user.id, is_read=False).count()
        for user in items
    }
    return render_template(
        "admin/users.html", items=items, addition_counts=addition_counts, unread_counts=unread_counts
    )


@bp.route("/users/<int:user_id>")
@login_required
def user_detail(user_id):
    user = User.query.get_or_404(user_id)
    additions = []
    for content_type, spec in CONTENT_TYPES.items():
        for obj in spec["model"].query.filter_by(added_by_user_id=user_id).all():
            view_url = None
            if spec["view_endpoint"]:
                view_url = url_for(spec["view_endpoint"], slug=obj.slug)
            additions.append({
                "type": content_type,
                "label": spec["label"],
                "name": getattr(obj, spec["name_field"]),
                "obj": obj,
                "view_url": view_url,
            })

    thread = (
        Message.query.filter(
            db.or_(
                db.and_(Message.sender_user_id == user_id, Message.recipient_user_id.is_(None)),
                db.and_(Message.sender_user_id.is_(None), Message.recipient_user_id == user_id),
            )
        )
        .order_by(Message.created_at.asc())
        .all()
    )
    unread = [m for m in thread if m.sender_user_id == user_id and not m.is_read]
    for m in unread:
        m.is_read = True
    if unread:
        db.session.commit()

    return render_template("admin/user_detail.html", user=user, additions=additions, thread=thread)


@bp.route("/users/<int:user_id>/message", methods=["POST"])
@login_required
def message_user(user_id):
    User.query.get_or_404(user_id)
    body = (request.form.get("body") or "").strip()
    if body:
        db.session.add(Message(sender_user_id=None, recipient_user_id=user_id, body=body))
        db.session.commit()
        recipient = db.session.get(User, user_id)
        telegram_bot.notify_new_message(recipient, "Администрации", body, url_for("messages.thread_admin"))
        flash("Сообщение отправлено.", "success")
    return redirect(url_for("admin.user_detail", user_id=user_id))


@bp.route("/users/<int:user_id>/delete", methods=["POST"])
@login_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    # Добавления пользователя не удаляются вместе с ним — они остаются на
    # сайте, просто теряют указание автора (added_by_user_id). Удалить
    # конкретное добавление можно отдельно, кнопкой рядом с ним.
    for spec in CONTENT_TYPES.values():
        spec["model"].query.filter_by(added_by_user_id=user_id).update({"added_by_user_id": None})
    Message.query.filter_by(sender_user_id=user_id).delete()
    Message.query.filter_by(recipient_user_id=user_id).delete()
    email = user.email
    db.session.delete(user)
    db.session.commit()
    flash(f"Пользователь «{email}» удалён (его добавления остались на сайте, переписка удалена).", "info")
    return redirect(url_for("admin.users"))


@bp.route("/content/<content_type>/<int:item_id>/delete", methods=["POST"])
@login_required
def delete_content(content_type, item_id):
    spec = CONTENT_TYPES.get(content_type)
    if spec is None:
        abort(404)
    item = spec["model"].query.get_or_404(item_id)
    redirect_user_id = item.added_by_user_id
    db.session.delete(item)
    db.session.commit()
    flash(f"{spec['label']} удалено(а).", "info")
    if redirect_user_id:
        return redirect(url_for("admin.user_detail", user_id=redirect_user_id))
    return redirect(request.referrer or url_for("admin.users"))


@bp.route("/content/<content_type>/<int:item_id>/edit", methods=["GET", "POST"])
@login_required
def edit_content(content_type, item_id):
    spec = CONTENT_TYPES.get(content_type)
    if spec is None:
        abort(404)
    item = spec["model"].query.get_or_404(item_id)

    # Поля "жанр"/"рубрика" — подсказываем уже существующие значения, чтобы
    # не плодить дубли, отличающиеся только регистром/опечаткой.
    choice_field = {"book": "genre", "article": "category"}.get(content_type)
    extra_choices = {}
    if choice_field:
        column = getattr(spec["model"], choice_field)
        extra_choices[choice_field] = sorted(
            {row[0] for row in spec["model"].query.with_entities(column).distinct() if row[0]}
        )

    if request.method == "POST":
        for field_name, _label, field_type in spec["fields"]:
            raw = request.form.get(field_name)
            if field_type == "number":
                try:
                    value = float(raw) if raw not in (None, "") else None
                except ValueError:
                    value = getattr(item, field_name)
            elif field_name in extra_choices:
                value = match_existing(raw, extra_choices[field_name])
            else:
                value = (raw or "").strip() or None
            setattr(item, field_name, value)
        db.session.commit()
        flash(f"{spec['label']} изменено(а).", "success")
        if item.added_by_user_id:
            return redirect(url_for("admin.user_detail", user_id=item.added_by_user_id))
        return redirect(url_for("admin.users"))

    return render_template(
        "admin/edit_content.html", item=item, spec=spec, content_type=content_type, extra_choices=extra_choices
    )


@bp.route("/content/book/<int:book_id>/files/add", methods=["POST"])
@login_required
def add_book_files(book_id):
    book = Book.query.get_or_404(book_id)
    saved_files, errors = upload_book_files(request.files.getlist("book_files"))
    for info in saved_files:
        db.session.add(BookFile(book_id=book.id, **info))
    if saved_files:
        db.session.commit()
        flash(f"Добавлено файлов: {len(saved_files)}.", "success")
    for error in errors:
        flash(error, "info")
    return redirect(url_for("admin.edit_content", content_type="book", item_id=book.id))


@bp.route("/content/book/<int:book_id>/files/<int:file_id>/delete", methods=["POST"])
@login_required
def delete_book_file(book_id, file_id):
    book_file = BookFile.query.filter_by(id=file_id, book_id=book_id).first_or_404()
    db.session.delete(book_file)
    db.session.commit()
    flash("Файл удалён.", "info")
    return redirect(url_for("admin.edit_content", content_type="book", item_id=book_id))


@bp.route("/banners")
@login_required
def banners():
    by_slot = {b.slot: b for b in Banner.query.all()}
    items = [by_slot.get(slot) for slot in BANNER_SLOTS]
    return render_template("admin/banners.html", items=items, slots=BANNER_SLOTS)


@bp.route("/banners/<int:slot>/edit", methods=["GET", "POST"])
@login_required
def edit_banner(slot):
    if slot not in BANNER_SLOTS:
        abort(404)
    banner = Banner.query.filter_by(slot=slot).first()

    if request.method == "POST":
        banner_type = request.form.get("banner_type") or "text"
        if banner_type not in Banner.BANNER_TYPES:
            banner_type = "text"
        title = (request.form.get("title") or "").strip()
        content_url = (request.form.get("content_url") or "").strip()
        text_content = (request.form.get("text_content") or "").strip()
        link_url = (request.form.get("link_url") or "").strip()

        if banner_type == "image":
            uploaded_url, photo_error = upload_photo(request.files.get("image_file"))
            if uploaded_url:
                content_url = uploaded_url
            elif photo_error:
                flash(photo_error, "info")

        if banner is None:
            banner = Banner(slot=slot)
            db.session.add(banner)

        banner.banner_type = banner_type
        banner.title = title or None
        banner.content_url = content_url or None
        banner.text_content = text_content or None
        banner.link_url = link_url or None
        db.session.commit()

        flash(f"Баннер {slot} сохранён.", "success")
        return redirect(url_for("admin.banners"))

    return render_template("admin/banner_edit.html", banner=banner, slot=slot)


@bp.route("/banners/<int:slot>/clear", methods=["POST"])
@login_required
def clear_banner(slot):
    banner = Banner.query.filter_by(slot=slot).first()
    if banner is not None:
        db.session.delete(banner)
        db.session.commit()
        flash(f"Баннер {slot} очищен.", "info")
    return redirect(url_for("admin.banners"))


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
