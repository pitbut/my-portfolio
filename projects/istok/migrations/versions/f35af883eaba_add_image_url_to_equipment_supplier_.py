"""add image_url to equipment, supplier, review

Revision ID: f35af883eaba
Revises: 468b80510498
Create Date: 2026-08-04 05:48:41.446554

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f35af883eaba'
down_revision = '468b80510498'
branch_labels = None
depends_on = None


def upgrade():
    # Все три колонки nullable — просто добавляются, без backfill, безопасно
    # и на уже заполненных таблицах.
    with op.batch_alter_table('equipment', schema=None) as batch_op:
        batch_op.add_column(sa.Column('image_url', sa.String(length=500), nullable=True))

    with op.batch_alter_table('suppliers', schema=None) as batch_op:
        batch_op.add_column(sa.Column('image_url', sa.String(length=500), nullable=True))

    with op.batch_alter_table('reviews', schema=None) as batch_op:
        batch_op.add_column(sa.Column('image_url', sa.String(length=500), nullable=True))


def downgrade():
    with op.batch_alter_table('reviews', schema=None) as batch_op:
        batch_op.drop_column('image_url')

    with op.batch_alter_table('suppliers', schema=None) as batch_op:
        batch_op.drop_column('image_url')

    with op.batch_alter_table('equipment', schema=None) as batch_op:
        batch_op.drop_column('image_url')
