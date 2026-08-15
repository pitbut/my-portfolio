"""Лёгкая авто-миграция без Alembic: db.create_all() создаёт только НОВЫЕ таблицы,
но не добавляет новые колонки в уже существующие (например, когда мы добавили
оформление витрины в Shop уже после первого деплоя на Render). Эта функция
проверяет, каких колонок не хватает, и досоздаёт их через ALTER TABLE."""
from sqlalchemy import inspect, text

# таблица -> {колонка: SQL-тип}
EXPECTED_COLUMNS = {
    "shop": {
        "wall_color": "VARCHAR(20)",
        "floor_color": "VARCHAR(20)",
        "has_window": "BOOLEAN",
        "has_painting": "BOOLEAN",
        "has_plant": "BOOLEAN",
    },
    "order": {
        "buyer_id": "INTEGER",
    },
    "product": {
        "is_removed": "BOOLEAN",
    },
}


def run_light_migrations(db):
    inspector = inspect(db.engine)
    existing_tables = set(inspector.get_table_names())
    for table, columns in EXPECTED_COLUMNS.items():
        if table not in existing_tables:
            continue  # таблицы ещё нет - её создаст db.create_all(), новые колонки будут сразу
        existing_cols = {c["name"] for c in inspector.get_columns(table)}
        for col_name, col_type in columns.items():
            if col_name not in existing_cols:
                db.session.execute(text(f'ALTER TABLE "{table}" ADD COLUMN {col_name} {col_type}'))
    db.session.commit()
