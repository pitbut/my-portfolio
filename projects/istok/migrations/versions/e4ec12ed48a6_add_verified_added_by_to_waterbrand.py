"""Add verified/added_by_user_id to WaterBrand

Revision ID: e4ec12ed48a6
Revises: a7989a3058b6
Create Date: 2026-08-16 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e4ec12ed48a6'
down_revision = 'a7989a3058b6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('water_brands', schema=None) as batch_op:
        batch_op.add_column(sa.Column('verified', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('added_by_user_id', sa.Integer(), nullable=True))

    connection = op.get_bind()
    water_brands = sa.table("water_brands", sa.column("verified", sa.Boolean))
    # существующие марки (из CSV/каталога) считаем уже доверенными —
    # "не проверено" получают только новые, добавленные пользователями
    # через сайт (см. app/routes/catalog.py).
    connection.execute(water_brands.update().values(verified=True))

    with op.batch_alter_table('water_brands', schema=None) as batch_op:
        batch_op.alter_column('verified', existing_type=sa.Boolean(), nullable=False)
        batch_op.create_foreign_key(
            'fk_water_brands_added_by_user_id_users', 'users', ['added_by_user_id'], ['id']
        )


def downgrade():
    with op.batch_alter_table('water_brands', schema=None) as batch_op:
        batch_op.drop_constraint('fk_water_brands_added_by_user_id_users', type_='foreignkey')
        batch_op.drop_column('added_by_user_id')
        batch_op.drop_column('verified')
