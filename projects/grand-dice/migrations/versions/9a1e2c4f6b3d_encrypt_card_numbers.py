"""encrypt card numbers at rest

Revision ID: 9a1e2c4f6b3d
Revises: c5ad6f0374b0
Create Date: 2026-08-15 15:30:00.000000

"""
import os

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9a1e2c4f6b3d'
down_revision = 'c5ad6f0374b0'
branch_labels = None
depends_on = None


def _get_fernet():
    from cryptography.fernet import Fernet

    key = os.environ.get("CARD_ENCRYPTION_KEY")
    if not key:
        raise RuntimeError(
            "CARD_ENCRYPTION_KEY не задан в окружении — установите его в .env "
            "перед выполнением этой миграции (нужен, чтобы зашифровать уже "
            "сохранённые номера карт)."
        )
    return Fernet(key)


def _encrypt_column(bind, fernet, table_name):
    table = sa.table(
        table_name, sa.column("id", sa.Integer), sa.column("card_number", sa.Text)
    )
    rows = bind.execute(
        sa.select(table.c.id, table.c.card_number).where(table.c.card_number.isnot(None))
    ).fetchall()
    for row in rows:
        encrypted = fernet.encrypt(row.card_number.encode()).decode()
        bind.execute(table.update().where(table.c.id == row.id).values(card_number=encrypted))


def upgrade():
    # Расширяем колонку: зашифрованный токен (Fernet) заметно длиннее
    # исходного номера карты и не помещается в String(32).
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column(
            'card_number', existing_type=sa.String(length=32), type_=sa.Text(), existing_nullable=True
        )

    with op.batch_alter_table('wallet_requests', schema=None) as batch_op:
        batch_op.alter_column(
            'card_number', existing_type=sa.String(length=32), type_=sa.Text(), existing_nullable=True
        )

    # Шифруем номера карт, сохранённые в открытом виде до появления
    # шифрования — иначе они так и останутся читаемыми в базе.
    fernet = _get_fernet()
    bind = op.get_bind()
    _encrypt_column(bind, fernet, "users")
    _encrypt_column(bind, fernet, "wallet_requests")


def downgrade():
    # Расшифровка задним числом не выполняется — откатывается только тип
    # колонки. Если понадобится откат, значения останутся зашифрованными.
    with op.batch_alter_table('wallet_requests', schema=None) as batch_op:
        batch_op.alter_column(
            'card_number', existing_type=sa.Text(), type_=sa.String(length=32), existing_nullable=True
        )

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column(
            'card_number', existing_type=sa.Text(), type_=sa.String(length=32), existing_nullable=True
        )
