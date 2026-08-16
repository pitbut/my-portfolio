"""Add messages table (user<->user and user<->admin chat)

Revision ID: b51725cfaa19
Revises: 4a6cc13c83e3
Create Date: 2026-08-16 21:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b51725cfaa19'
down_revision = '4a6cc13c83e3'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('sender_user_id', sa.Integer(), nullable=True),
        sa.Column('recipient_user_id', sa.Integer(), nullable=True),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('is_read', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['sender_user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['recipient_user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('messages', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_messages_sender_user_id'), ['sender_user_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_messages_recipient_user_id'), ['recipient_user_id'], unique=False)


def downgrade():
    with op.batch_alter_table('messages', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_messages_recipient_user_id'))
        batch_op.drop_index(batch_op.f('ix_messages_sender_user_id'))
    op.drop_table('messages')
