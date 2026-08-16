"""Add banners table

Revision ID: 2e64d9a5e08c
Revises: cd077dba1954
Create Date: 2026-08-16 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2e64d9a5e08c'
down_revision = 'cd077dba1954'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'banners',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('slot', sa.Integer(), nullable=False),
        sa.Column('banner_type', sa.String(length=20), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('content_url', sa.String(length=500), nullable=True),
        sa.Column('text_content', sa.Text(), nullable=True),
        sa.Column('link_url', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slot'),
    )


def downgrade():
    op.drop_table('banners')
