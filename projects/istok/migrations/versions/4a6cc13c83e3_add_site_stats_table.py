"""Add site_stats table (visit counter)

Revision ID: 4a6cc13c83e3
Revises: 2e64d9a5e08c
Create Date: 2026-08-16 19:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4a6cc13c83e3'
down_revision = '2e64d9a5e08c'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'site_stats',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('total_views', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    site_stats = sa.table("site_stats", sa.column("id", sa.Integer), sa.column("total_views", sa.Integer))
    op.get_bind().execute(site_stats.insert().values(id=1, total_views=0))


def downgrade():
    op.drop_table('site_stats')
