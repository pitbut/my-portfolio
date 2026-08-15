"""Локальный запуск: пересоздаёт таблицы с нуля и наполняет 2 тестовых магазина.
На Render это делать не нужно - там наполнение происходит автоматически при
старте приложения (см. seed_if_empty() в app.py), т.к. Shell недоступен на free-тарифе."""
from app import app
from models import db
from seed_data import seed_if_empty

with app.app_context():
    db.drop_all()
    db.create_all()
    seed_if_empty()
    print("Готово: 2 тестовых магазина созданы.")
