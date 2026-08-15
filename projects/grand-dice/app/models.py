"""SQLAlchemy-модели Grand Dice Casino."""
from datetime import datetime

from app import db


class TimestampMixin:
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class User(TimestampMixin, db.Model):
    """Зарегистрированный игрок (или админ, если is_admin=True)."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    email_confirmed = db.Column(db.Boolean, nullable=False, default=False)
    confirmed_at = db.Column(db.DateTime, nullable=True)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)

    # Номер карты для выплат при выводе средств — админ смотрит его при
    # обработке заявки на вывод (пока Click API не подключён, перевод идёт
    # вручную на эту карту).
    card_number = db.Column(db.String(32), nullable=True)

    # Блокировка аккаунта администратором. is_blocked — бессрочная ручная
    # блокировка; blocked_until — временная (снимается сама по истечении).
    # Оба поля могут быть выставлены одновременно, действует любое из них.
    is_blocked = db.Column(db.Boolean, nullable=False, default=False)
    blocked_until = db.Column(db.DateTime, nullable=True)
    blocked_reason = db.Column(db.String(255), nullable=True)

    support_messages = db.relationship(
        "SupportMessage",
        backref="user",
        lazy="dynamic",
        foreign_keys="SupportMessage.user_id",
        cascade="all, delete-orphan",
    )

    # Реальный баланс — деньги, которые в будущем будут заводиться/выводиться
    # через Click API. Пока приём/выдача идут как заявки, обрабатываемые
    # администратором вручную (см. WalletRequest).
    real_balance = db.Column(db.Numeric(12, 2), nullable=False, default=0)

    # Демо-баланс — виртуальные средства для тестового режима, реальных
    # денег не касается. Пополняется бесплатно самим пользователем.
    demo_balance = db.Column(db.Numeric(12, 2), nullable=False, default=0)

    rounds = db.relationship(
        "GameRound", backref="user", lazy="dynamic", cascade="all, delete-orphan"
    )
    wallet_requests = db.relationship(
        "WalletRequest",
        backref="user",
        lazy="dynamic",
        foreign_keys="WalletRequest.user_id",
        cascade="all, delete-orphan",
    )

    # --- интерфейс, ожидаемый Flask-Login ---
    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

    def balance_for(self, mode):
        return self.real_balance if mode == "real" else self.demo_balance

    def is_currently_blocked(self):
        if self.is_blocked:
            return True
        if self.blocked_until and self.blocked_until > datetime.utcnow():
            return True
        return False

    def __repr__(self):
        return f"<User {self.email!r}>"


class GameRound(db.Model):
    """Один раунд игры в кости."""

    __tablename__ = "game_rounds"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    mode = db.Column(db.String(10), nullable=False)  # 'real' | 'demo'
    direction = db.Column(db.String(10), nullable=False)  # 'under' | 'over'
    target = db.Column(db.Numeric(5, 2), nullable=False)  # порог 2.00-98.00
    roll = db.Column(db.Numeric(5, 2), nullable=False)  # выпавшее число 0.00-99.99

    bet_amount = db.Column(db.Numeric(12, 2), nullable=False)
    multiplier = db.Column(db.Numeric(10, 4), nullable=False)
    payout = db.Column(db.Numeric(12, 2), nullable=False)  # 0, если проигрыш
    win = db.Column(db.Boolean, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<GameRound user={self.user_id} {self.direction} {self.target} roll={self.roll}>"


class WalletRequest(db.Model):
    """Заявка на пополнение или вывод реальных средств.

    Пока не подключён Click API, деньги реально не двигаются автоматически:
    администратор обрабатывает заявку вручную и меняет её статус. Для
    вывода дополнительно требуется подтверждение OTP-кодом, отправленным на
    email, прежде чем заявка попадёт в очередь администратора.
    """

    __tablename__ = "wallet_requests"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    kind = db.Column(db.String(10), nullable=False)  # 'deposit' | 'withdraw'
    amount = db.Column(db.Numeric(12, 2), nullable=False)

    # Снимок номера карты пользователя на момент заявки (для вывода) — так
    # админ видит, куда переводить, даже если пользователь потом сменит
    # карту в профиле.
    card_number = db.Column(db.String(32), nullable=True)

    # awaiting_otp -> pending -> approved | rejected
    # (awaiting_otp применяется только к выводу; депозит сразу pending)
    status = db.Column(db.String(20), nullable=False, default="pending")

    otp_hash = db.Column(db.String(255), nullable=True)
    otp_expires_at = db.Column(db.DateTime, nullable=True)
    otp_attempts = db.Column(db.Integer, nullable=False, default=0)

    admin_note = db.Column(db.String(500), nullable=True)
    processed_at = db.Column(db.DateTime, nullable=True)
    processed_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    processed_by = db.relationship("User", foreign_keys=[processed_by_id])

    def __repr__(self):
        return f"<WalletRequest {self.kind} user={self.user_id} {self.amount} [{self.status}]>"


class SupportMessage(db.Model):
    """Сообщение в переписке игрок-администратор (один тред на игрока).

    user_id — чей это тред (всегда игрок, не админ). sender_is_admin
    различает, кто написал конкретное сообщение внутри треда.
    """

    __tablename__ = "support_messages"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    sender_is_admin = db.Column(db.Boolean, nullable=False, default=False)

    body = db.Column(db.Text, nullable=True)
    photo_filename = db.Column(db.String(255), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        who = "admin" if self.sender_is_admin else "user"
        return f"<SupportMessage user={self.user_id} from={who}>"
