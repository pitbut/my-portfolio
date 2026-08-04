"""equipment catalog, book/experiment/delivery slugs, reviews

Revision ID: 468b80510498
Revises: b62229c7ade7
Create Date: 2026-08-04 05:01:06.441048

"""
import re

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '468b80510498'
down_revision = 'b62229c7ade7'
branch_labels = None
depends_on = None


_TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}


def _slugify(name, fallback):
    """Транслитерация кириллицы + приведение к URL-безопасному виду."""
    lowered = (name or "").lower()
    transliterated = "".join(_TRANSLIT.get(ch, ch) for ch in lowered)
    slug = re.sub(r"[^a-z0-9]+", "-", transliterated).strip("-")
    return slug or fallback


def _backfill_slug(connection, table_name, source_column, fallback):
    """Добавляет nullable slug, заполняет его по source_column с де-дупликацией,
    затем делает NOT NULL + уникальный индекс — безопасно и для уже
    заполненных таблиц (продакшен), и для пустых (тесты/новая база)."""
    with op.batch_alter_table(table_name, schema=None) as batch_op:
        batch_op.add_column(sa.Column('slug', sa.String(length=220), nullable=True))

    table = sa.table(
        table_name,
        sa.column("id", sa.Integer),
        sa.column(source_column, sa.String),
        sa.column("slug", sa.String),
    )
    rows = connection.execute(sa.select(table.c.id, getattr(table.c, source_column))).fetchall()
    used_slugs = set()
    for row in rows:
        base = _slugify(getattr(row, source_column), fallback)
        slug = base
        n = 2
        while slug in used_slugs:
            slug = f"{base}-{n}"
            n += 1
        used_slugs.add(slug)
        connection.execute(table.update().where(table.c.id == row.id).values(slug=slug))

    with op.batch_alter_table(table_name, schema=None) as batch_op:
        batch_op.alter_column('slug', existing_type=sa.String(length=220), nullable=False)
        batch_op.create_index(batch_op.f(f'ix_{table_name}_slug'), ['slug'], unique=True)


def upgrade():
    connection = op.get_bind()

    op.create_table(
        'reviews',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('target_type', sa.String(length=50), nullable=False),
        sa.Column('target_id', sa.Integer(), nullable=False),
        sa.Column('author_name', sa.String(length=120), nullable=True),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('reviews', schema=None) as batch_op:
        batch_op.create_index('ix_reviews_target_type', ['target_type'], unique=False)
        batch_op.create_index('ix_reviews_target_id', ['target_id'], unique=False)

    # equipment: slug + модерация пользовательских добавлений (как у Supplier)
    with op.batch_alter_table('equipment', schema=None) as batch_op:
        batch_op.add_column(sa.Column('verified', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('added_by_user_id', sa.Integer(), nullable=True))

    equipment = sa.table("equipment", sa.column("verified", sa.Boolean))
    # существующее (загруженное из CSV/добавленное админом) оборудование
    # считаем уже проверенным — непроверенным будет только новое,
    # добавленное пользователями через сайт.
    connection.execute(equipment.update().values(verified=True))

    with op.batch_alter_table('equipment', schema=None) as batch_op:
        batch_op.alter_column('verified', existing_type=sa.Boolean(), nullable=False)
        batch_op.create_foreign_key(
            'fk_equipment_added_by_user_id_users', 'users', ['added_by_user_id'], ['id']
        )

    _backfill_slug(connection, 'equipment', 'name', 'equipment')
    _backfill_slug(connection, 'books', 'title', 'book')
    _backfill_slug(connection, 'experiments', 'title', 'experiment')
    _backfill_slug(connection, 'delivery_services', 'name', 'service')


def downgrade():
    with op.batch_alter_table('delivery_services', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_delivery_services_slug'))
        batch_op.drop_column('slug')

    with op.batch_alter_table('experiments', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_experiments_slug'))
        batch_op.drop_column('slug')

    with op.batch_alter_table('books', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_books_slug'))
        batch_op.drop_column('slug')

    with op.batch_alter_table('equipment', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_equipment_slug'))
        batch_op.drop_column('slug')
        batch_op.drop_constraint('fk_equipment_added_by_user_id_users', type_='foreignkey')
        batch_op.drop_column('added_by_user_id')
        batch_op.drop_column('verified')

    with op.batch_alter_table('reviews', schema=None) as batch_op:
        batch_op.drop_index('ix_reviews_target_id')
        batch_op.drop_index('ix_reviews_target_type')

    op.drop_table('reviews')
