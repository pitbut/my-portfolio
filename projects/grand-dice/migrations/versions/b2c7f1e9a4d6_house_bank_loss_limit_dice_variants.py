"""house bank, session loss limit, two-dice/four-dice variants, deposit receipts

Revision ID: b2c7f1e9a4d6
Revises: 9a1e2c4f6b3d
Create Date: 2026-08-15 16:20:00.000000

"""
from datetime import datetime

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b2c7f1e9a4d6'
down_revision = '9a1e2c4f6b3d'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'casino_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('house_bank', sa.Numeric(14, 2), nullable=False, server_default='0'),
        sa.Column('loss_limit_percent', sa.Numeric(5, 2), nullable=False, server_default='30'),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    casino_settings = sa.table(
        'casino_settings',
        sa.column('id', sa.Integer),
        sa.column('house_bank', sa.Numeric),
        sa.column('loss_limit_percent', sa.Numeric),
        sa.column('updated_at', sa.DateTime),
    )
    op.bulk_insert(
        casino_settings,
        [{'id': 1, 'house_bank': 0, 'loss_limit_percent': 30, 'updated_at': datetime.utcnow()}],
    )

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('session_start_balance', sa.Numeric(12, 2), nullable=True))
        batch_op.add_column(sa.Column('real_play_locked_until', sa.DateTime(), nullable=True))

    with op.batch_alter_table('wallet_requests', schema=None) as batch_op:
        batch_op.add_column(sa.Column('receipt_filename', sa.String(length=255), nullable=True))

    with op.batch_alter_table('game_rounds', schema=None) as batch_op:
        # game_type NOT NULL на уже заполненной таблице — нужен server_default,
        # иначе Postgres откажет существующим строкам (см. миграцию c5ad6f0374b0).
        batch_op.add_column(
            sa.Column('game_type', sa.String(length=20), nullable=False, server_default='classic')
        )
        batch_op.add_column(
            sa.Column('push', sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.add_column(sa.Column('dice_json', sa.Text(), nullable=True))
        # Ослабляем NOT NULL — четырёхкостный покер не использует direction/target/roll.
        batch_op.alter_column('direction', existing_type=sa.String(length=10), nullable=True)
        batch_op.alter_column('target', existing_type=sa.Numeric(5, 2), nullable=True)
        batch_op.alter_column('roll', existing_type=sa.Numeric(5, 2), nullable=True)


def downgrade():
    with op.batch_alter_table('game_rounds', schema=None) as batch_op:
        batch_op.alter_column('roll', existing_type=sa.Numeric(5, 2), nullable=False)
        batch_op.alter_column('target', existing_type=sa.Numeric(5, 2), nullable=False)
        batch_op.alter_column('direction', existing_type=sa.String(length=10), nullable=False)
        batch_op.drop_column('dice_json')
        batch_op.drop_column('push')
        batch_op.drop_column('game_type')

    with op.batch_alter_table('wallet_requests', schema=None) as batch_op:
        batch_op.drop_column('receipt_filename')

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('real_play_locked_until')
        batch_op.drop_column('session_start_balance')

    op.drop_table('casino_settings')
