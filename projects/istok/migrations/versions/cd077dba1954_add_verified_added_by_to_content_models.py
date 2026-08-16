"""Add verified/added_by_user_id to Book, Article, SacredSource, Experiment, DeliveryService

Revision ID: cd077dba1954
Revises: e4ec12ed48a6
Create Date: 2026-08-16 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'cd077dba1954'
down_revision = 'e4ec12ed48a6'
branch_labels = None
depends_on = None

TABLES = ["books", "articles", "sacred_sources", "experiments", "delivery_services"]


def upgrade():
    connection = op.get_bind()
    for table in TABLES:
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.add_column(sa.Column('verified', sa.Boolean(), nullable=True))
            batch_op.add_column(sa.Column('added_by_user_id', sa.Integer(), nullable=True))

        t = sa.table(table, sa.column("verified", sa.Boolean))
        # существующий контент (из CSV/админа) считаем уже доверенным —
        # "не проверено" получают только новые записи, добавленные
        # пользователями через сайт.
        connection.execute(t.update().values(verified=True))

        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.alter_column('verified', existing_type=sa.Boolean(), nullable=False)
            batch_op.create_foreign_key(
                f'fk_{table}_added_by_user_id_users', 'users', ['added_by_user_id'], ['id']
            )


def downgrade():
    for table in TABLES:
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.drop_constraint(f'fk_{table}_added_by_user_id_users', type_='foreignkey')
            batch_op.drop_column('added_by_user_id')
            batch_op.drop_column('verified')
