from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'buyer' | 'seller'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Shop(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, default="")
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    products = db.relationship("Product", backref="shop", lazy=True)
    # --- простое оформление витрины ---
    wall_color = db.Column(db.String(20), default="#141821")
    floor_color = db.Column(db.String(20), default="#11141c")
    has_window = db.Column(db.Boolean, default=False)
    has_painting = db.Column(db.Boolean, default=False)
    has_plant = db.Column(db.Boolean, default=False)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey("shop.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(80), default="")
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, default="")
    model_file = db.Column(db.String(200), nullable=False)  # filename in static/models or uploads
    shelf_x = db.Column(db.Float, default=0.0)  # position on the shelf (demo layout)
    is_removed = db.Column(db.Boolean, default=False)  # мягкое удаление - если уже есть заказы


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    buyer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    price = db.Column(db.Float, nullable=False)
    address = db.Column(db.String(300), default="")
    lat = db.Column(db.Float, nullable=True)
    lng = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(30), default="ожидает подтверждения оплаты")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    target_type = db.Column(db.String(20), nullable=False)  # 'product' | 'shop'
    target_id = db.Column(db.Integer, nullable=False)
    author = db.Column(db.String(80), default="Гость")
    rating = db.Column(db.Integer, default=5)
    text = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Invite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(12), unique=True, nullable=False)
    shop_id = db.Column(db.Integer, db.ForeignKey("shop.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
