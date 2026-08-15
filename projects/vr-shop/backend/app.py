import os
import uuid
from collections import defaultdict
from functools import wraps
from flask import Flask, request, jsonify, render_template, send_from_directory, redirect, url_for, flash
from flask_login import (
    LoginManager, login_user, logout_user, login_required, current_user,
)
from flask_socketio import SocketIO, emit, join_room, leave_room
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Shop, Product, Order, Review, Invite
from storage import upload_model, storage_enabled

BASE_DIR = os.path.dirname(__file__)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only-insecure-key-change-me")

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# --- БД: на Render подставляется DATABASE_URL (Postgres), локально - SQLite ---
db_url = os.environ.get("DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'shop.db')}")
if db_url.startswith("postgres://"):  # Render/Heroku иногда отдают старую схему
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_DIR"] = os.path.join(BASE_DIR, "uploads")  # используется только как запасной вариант
os.makedirs(app.config["UPLOAD_DIR"], exist_ok=True)

db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = "login_page"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


with app.app_context():
    db.create_all()  # создаёт таблицы при первом запуске (в т.ч. на чистой Postgres-базе Render)
    from migrations_lite import run_light_migrations
    run_light_migrations(db)  # досоздаёт колонки, которых не было в уже существующих таблицах
    from seed_data import seed_if_empty
    seed_if_empty()  # наполняет 2 тестовых магазина, если база пустая (нет доступа к Shell на free-тарифе)

ALLOWED_EXT = {"glb", "gltf"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


def seller_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("login_page"))
        if current_user.role != "seller":
            return "Доступно только для продавцов", 403
        return fn(*args, **kwargs)
    return wrapper


# ---------- регистрация / вход ----------

@app.route("/register", methods=["GET", "POST"])
def register_page():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "buyer")
        if role not in ("buyer", "seller"):
            role = "buyer"
        if not username or not password:
            flash("Заполните имя пользователя и пароль")
            return render_template("register.html")
        if User.query.filter_by(username=username).first():
            flash("Такое имя пользователя уже занято")
            return render_template("register.html")
        user = User(username=username, password_hash=generate_password_hash(password), role=role)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for("seller_dashboard" if role == "seller" else "account_page"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login_page():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for("seller_dashboard" if user.role == "seller" else "account_page"))
        flash("Неверное имя пользователя или пароль")
    return render_template("login.html")


@app.route("/logout")
def logout_page():
    logout_user()
    return redirect(url_for("index"))


# ---------- страницы ----------

@app.route("/")
def index():
    q = request.args.get("q", "").strip()
    shops = Shop.query.all()
    results = None
    if q:
        like = f"%{q}%"
        results = (
            Product.query.filter(db.or_(Product.name.ilike(like), Product.category.ilike(like))).all()
        )
    return render_template("index.html", shops=shops, query=q, results=results)


@app.route("/shop/<int:shop_id>")
def shop_page(shop_id):
    shop = Shop.query.get_or_404(shop_id)
    return render_template("shop.html", shop=shop)


@app.route("/account")
@login_required
def account_page():
    if current_user.role == "seller":
        return redirect(url_for("seller_dashboard"))
    orders = (
        Order.query.filter_by(buyer_id=current_user.id)
        .order_by(Order.created_at.desc()).all()
    )
    order_rows = []
    for o in orders:
        product = Product.query.get(o.product_id)
        order_rows.append({
            "order": o,
            "product_name": product.name if product else "(товар удалён)",
            "shop_name": product.shop.name if product else "",
        })
    return render_template("account.html", order_rows=order_rows)


@app.route("/seller/dashboard")
@seller_required
def seller_dashboard():
    shops = Shop.query.filter_by(owner_id=current_user.id).all()
    products_by_shop = {
        shop.id: Product.query.filter_by(shop_id=shop.id, is_removed=False).all()
        for shop in shops
    }
    return render_template("seller_dashboard.html", shops=shops, products_by_shop=products_by_shop)


@app.route("/seller/shops", methods=["POST"])
@seller_required
def create_shop():
    name = request.form.get("name", "").strip() or "Мой магазин"
    description = request.form.get("description", "")
    shop = Shop(
        name=name, description=description, owner_id=current_user.id,
        wall_color=request.form.get("wall_color", "#141821"),
        floor_color=request.form.get("floor_color", "#11141c"),
        has_window="has_window" in request.form,
        has_painting="has_painting" in request.form,
        has_plant="has_plant" in request.form,
    )
    db.session.add(shop)
    db.session.commit()
    return redirect(url_for("seller_dashboard"))


# ---------- статика для 3D-моделей (сгенерированные тестовые + загруженные продавцом) ----------

@app.route("/models/<path:filename>")
def serve_model(filename):
    return send_from_directory(os.path.join(BASE_DIR, "static", "models"), filename)


@app.route("/uploads/<path:filename>")
def serve_upload(filename):
    return send_from_directory(app.config["UPLOAD_DIR"], filename)


# ---------- API: магазины и товары ----------

@app.route("/api/shops")
def api_shops():
    shops = Shop.query.all()
    return jsonify([{"id": s.id, "name": s.name, "description": s.description} for s in shops])


@app.route("/api/shops/<int:shop_id>")
def api_shop_detail(shop_id):
    s = Shop.query.get_or_404(shop_id)
    return jsonify({
        "id": s.id, "name": s.name, "description": s.description,
        "wall_color": s.wall_color, "floor_color": s.floor_color,
        "has_window": s.has_window, "has_painting": s.has_painting, "has_plant": s.has_plant,
    })


@app.route("/api/shops/<int:shop_id>/products")
def api_shop_products(shop_id):
    products = Product.query.filter_by(shop_id=shop_id, is_removed=False).all()
    return jsonify([_product_json(p) for p in products])


@app.route("/api/products/<int:product_id>")
def api_product(product_id):
    p = Product.query.get_or_404(product_id)
    return jsonify(_product_json(p))


def _product_json(p):
    # p.model_file может быть: полным URL (загружено в R2), именем в uploads/ (локальный fallback),
    # или именем встроенной тестовой заглушки в static/models/
    if p.model_file.startswith("http://") or p.model_file.startswith("https://"):
        model_url = p.model_file
    else:
        upload_path = os.path.join(app.config["UPLOAD_DIR"], p.model_file)
        model_url = f"/uploads/{p.model_file}" if os.path.exists(upload_path) else f"/models/{p.model_file}"
    return {
        "id": p.id, "shop_id": p.shop_id, "name": p.name, "category": p.category,
        "price": p.price, "description": p.description, "model_url": model_url,
        "shelf_x": p.shelf_x,
    }


# ---------- API: продавец загружает товар в СВОЙ магазин ----------

@app.route("/api/shops/<int:shop_id>/products", methods=["POST"])
@seller_required
def api_add_product(shop_id):
    shop = Shop.query.get_or_404(shop_id)
    if shop.owner_id != current_user.id:
        return jsonify({"error": "Это не ваш магазин"}), 403

    name = request.form.get("name", "Новый товар")
    price = float(request.form.get("price", 0) or 0)
    category = request.form.get("category", "")
    description = request.form.get("description", "")

    file = request.files.get("model")
    used_fallback = False
    if file and file.filename:
        if not allowed_file(file.filename):
            return jsonify({"error": "Разрешены только файлы .glb или .gltf"}), 400
        ext = file.filename.rsplit(".", 1)[1].lower()
        header = file.stream.read(4)
        file.stream.seek(0)
        if ext == "glb" and header != b"glTF":
            return jsonify({
                "error": "Файл не похож на настоящий бинарный GLB (нет заголовка glTF). "
                         "Экспортируйте модель как 'glTF Binary (.glb)' целиком в один файл "
                         "(в Blender: File → Export → glTF 2.0 → Format: glTF Binary)."
            }), 400
        stored_name = f"{uuid.uuid4().hex}.{ext}"
        remote_url = upload_model(file, stored_name)
        if remote_url:
            model_file = remote_url  # хранится в R2, в БД - полный URL
        else:
            file.stream.seek(0)
            file.save(os.path.join(app.config["UPLOAD_DIR"], stored_name))
            model_file = stored_name  # локальный fallback (для разработки)
    else:
        # без файла — ставим случайную тестовую заглушку, чтобы карточка не была пустой
        model_file = "test_box.glb"
        used_fallback = True

    existing = Product.query.filter_by(shop_id=shop_id).count()
    product = Product(
        shop_id=shop_id, name=name, category=category, price=price,
        description=description, model_file=model_file,
        shelf_x=(existing % 5 - 2) * 1.2,
    )
    db.session.add(product)
    db.session.commit()
    result = _product_json(product)
    result["used_fallback"] = used_fallback
    return jsonify(result), 201


@app.route("/api/products/<int:product_id>", methods=["DELETE"])
@seller_required
def api_delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    if product.shop.owner_id != current_user.id:
        return jsonify({"error": "Это не ваш товар"}), 403
    has_orders = Order.query.filter_by(product_id=product.id).count() > 0
    if has_orders:
        product.is_removed = True  # покупки уже есть - скрываем, но не удаляем (история заказов не сломается)
        db.session.commit()
        return jsonify({"ok": True, "soft_deleted": True})
    db.session.delete(product)
    db.session.commit()
    return jsonify({"ok": True, "soft_deleted": False})


# ---------- API: отзывы ----------

@app.route("/api/reviews/<target_type>/<int:target_id>")
def api_get_reviews(target_type, target_id):
    reviews = Review.query.filter_by(target_type=target_type, target_id=target_id).all()
    return jsonify([{"author": r.author, "rating": r.rating, "text": r.text} for r in reviews])


@app.route("/api/reviews", methods=["POST"])
def api_add_review():
    data = request.get_json(force=True)
    author = current_user.username if current_user.is_authenticated else data.get("author", "Гость")
    r = Review(
        target_type=data["target_type"], target_id=data["target_id"],
        author=author, rating=data.get("rating", 5),
        text=data.get("text", ""),
    )
    db.session.add(r)
    db.session.commit()
    return jsonify({"ok": True}), 201


# ---------- API: заказ (демо — ручной перевод по номеру карты) ----------

CARD_NUMBER_DEMO = "8600 1234 5678 9012"  # тестовый номер, для реальной системы подключить эквайринг


@app.route("/api/orders", methods=["POST"])
@login_required
def api_create_order():
    data = request.get_json(force=True)
    product = Product.query.get_or_404(data["product_id"])
    order = Order(
        buyer_id=current_user.id, product_id=product.id, price=product.price,
        address=data.get("address", ""), lat=data.get("lat"), lng=data.get("lng"),
    )
    db.session.add(order)
    db.session.commit()
    return jsonify({"order_id": order.id, "card_number": CARD_NUMBER_DEMO, "status": order.status}), 201


# ---------- API: пригласить друзей в сессию магазина ----------

@app.route("/api/shops/<int:shop_id>/invite", methods=["POST"])
def api_create_invite(shop_id):
    Shop.query.get_or_404(shop_id)
    code = uuid.uuid4().hex[:8]
    db.session.add(Invite(code=code, shop_id=shop_id))
    db.session.commit()
    return jsonify({"code": code, "url": f"/shop/{shop_id}?invite={code}"})


# ============================================================
# WebSocket: синхронизация выбора товара + голосовой чат (WebRTC signaling)
# ============================================================
# Комнаты: shop_<id>            - все, кто в этом магазине (для синхронизации выбора товара)
#          voice_<id>_all       - голосовой канал "все" (продавец + покупатель + друзья)
#          voice_<id>_friends   - голосовой канал "только друзья" (продавца туда не пускаем)
#
# Голосовая связь и установка соединений — через PeerJS (публичный бесплатный
# облачный брокер PeerJS сам берёт на себя WebRTC-хендшейк и STUN/TURN).
# Flask-SocketIO здесь используется только для обмена PeerJS-идентификаторами
# между участниками комнаты — то есть ровно тот подход, что уже проверенно
# работал в похожем проекте (VR-кафе с голосовым чатом).

voice_room_members = defaultdict(dict)  # room_name -> {sid: peer_id}


@socketio.on("join_shop")
def on_join_shop(data):
    shop_id = data.get("shop_id")
    if shop_id is None:
        return
    join_room(f"shop_{shop_id}")


@socketio.on("select_product")
def on_select_product(data):
    shop_id = data.get("shop_id")
    product_id = data.get("product_id")
    if shop_id is None or product_id is None:
        return
    emit("product_selected", {"product_id": product_id}, room=f"shop_{shop_id}", include_self=False)


@socketio.on("join_voice")
def on_join_voice(data):
    shop_id = data.get("shop_id")
    channel = data.get("channel")  # 'all' | 'friends'
    peer_id = data.get("peer_id")  # собственный PeerJS ID клиента
    if channel not in ("all", "friends") or shop_id is None or not peer_id:
        return
    if channel == "friends":
        shop = Shop.query.get(shop_id)
        if shop and current_user.is_authenticated and current_user.id == shop.owner_id:
            emit("voice_error", {"message": "Продавцу недоступен канал только для друзей"})
            return
    room_name = f"voice_{shop_id}_{channel}"
    existing_peer_ids = list(voice_room_members[room_name].values())
    join_room(room_name)
    voice_room_members[room_name][request.sid] = peer_id
    emit("voice_existing_peers", {"peer_ids": existing_peer_ids})


@socketio.on("leave_voice")
def on_leave_voice(data):
    shop_id = data.get("shop_id")
    channel = data.get("channel")
    if shop_id is None or channel not in ("all", "friends"):
        return
    _leave_voice_room(f"voice_{shop_id}_{channel}")


def _leave_voice_room(room_name):
    leave_room(room_name)
    peer_id = voice_room_members[room_name].pop(request.sid, None)
    if peer_id:
        emit("voice_peer_left", {"peer_id": peer_id}, room=room_name, include_self=False)


@socketio.on("disconnect")
def on_disconnect():
    # убираем отключившегося из всех голосовых комнат, чтобы у остальных не висели мёртвые соединения
    for room_name, members in list(voice_room_members.items()):
        peer_id = members.pop(request.sid, None)
        if peer_id:
            emit("voice_peer_left", {"peer_id": peer_id}, room=room_name, include_self=False)


if __name__ == "__main__":
    socketio.run(app, debug=True, port=5050)
