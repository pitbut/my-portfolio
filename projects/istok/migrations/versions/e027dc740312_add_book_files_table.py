"""Add book_files table

Revision ID: e027dc740312
Revises: faecd55ec6d4
Create Date: 2026-08-29 10:33:40.659917

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'e027dc740312'
down_revision = 'faecd55ec6d4'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'book_files',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('book_id', sa.Integer(), nullable=False),
        sa.Column('format', sa.String(length=10), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('size_bytes', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['book_id'], ['books.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    op.drop_table('book_files')
