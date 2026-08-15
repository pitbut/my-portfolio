"""fx rate cache on casino_settings

Revision ID: c3d8e5a1f7b2
Revises: b2c7f1e9a4d6
Create Date: 2026-08-15 19:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c3d8e5a1f7b2'
down_revision = 'b2c7f1e9a4d6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('casino_settings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('fx_rates_json', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('fx_rates_updated_at', sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table('casino_settings', schema=None) as batch_op:
        batch_op.drop_column('fx_rates_updated_at')
        batch_op.drop_column('fx_rates_json')
