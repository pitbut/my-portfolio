"""SQLAlchemy-модели Grand Dice Casino."""
from datetime import datetime

from app import db
from app.crypto import decrypt_card_number, encrypt_card_number


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
    # вручную на эту карту). Хранится зашифрованным (Fernet, CARD_ENCRYPTION_KEY);
    # колонка в БД по-прежнему называется card_number, но содержит шифротекст —
    # доступ идёт через property card_number ниже, которое прозрачно
    # шифрует/расшифровывает, чтобы остальной код не менялся.
    _card_number = db.Column("card_number", db.Text, nullable=True)

    @property
    def card_number(self):
        return decrypt_card_number(self._card_number)

    @card_number.setter
    def card_number(self, value):
        self._card_number = encrypt_card_number(value)

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

    # Лимит проигрыша за сессию: снимок реального баланса на момент входа в
    # реальный режим (см. game.set_mode) и метка времени, до которой игрок
    # заблокирован в реальном режиме после достижения лимита (в процентах —
    # CasinoSettings.loss_limit_percent, ползунок админа).
    session_start_balance = db.Column(db.Numeric(12, 2), nullable=True)
    real_play_locked_until = db.Column(db.DateTime, nullable=True)

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
    """Один раунд игры в кости — классика, "два кубика" или "покер на костях"."""

    __tablename__ = "game_rounds"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    mode = db.Column(db.String(10), nullable=False)  # 'real' | 'demo'
    # 'classic' (1 кость 0-99.99) | 'two_dice' (сумма 2 костей) | 'four_dice' (покер на костях)
    game_type = db.Column(db.String(20), nullable=False, default="classic")

    # Направление/порог/бросок используются только режимом classic и
    # two_dice (для two_dice target/roll — целые суммы 2-12, хранятся как
    # Numeric без дробной части). В four_dice всегда NULL — там результат
    # хранится в dice_json.
    direction = db.Column(db.String(10), nullable=True)  # 'under' | 'over'
    target = db.Column(db.Numeric(5, 2), nullable=True)
    roll = db.Column(db.Numeric(5, 2), nullable=True)

    bet_amount = db.Column(db.Numeric(12, 2), nullable=False)
    multiplier = db.Column(db.Numeric(10, 4), nullable=False)
    payout = db.Column(db.Numeric(12, 2), nullable=False)  # 0, если проигрыш
    win = db.Column(db.Boolean, nullable=False)
    # Ничья с казино (пуш) — ставка вернулась за вычетом свопа, не выигрыш и не проигрыш.
    push = db.Column(db.Boolean, nullable=False, default=False)

    # Доп. данные броска для two_dice/four_dice (кости игрока/казино, руки) — JSON-текст.
    dice_json = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<GameRound user={self.user_id} {self.game_type} roll={self.roll}>"


class CasinoSettings(db.Model):
    """Единственная строка (id=1) с общими настройками казино, которые
    правит админ: банк, находящийся в игре, и лимит проигрыша за сессию."""

    __tablename__ = "casino_settings"

    id = db.Column(db.Integer, primary_key=True)

    # Банк казино "в игре" — растёт, когда казино выигрывает у игроков, и
    # уменьшается при выплатах. Никогда не должен уходить в минус: реальная
    # игра блокируется глобально, если банка не хватает на покрытие ставки.
    house_bank = db.Column(db.Numeric(14, 2), nullable=False, default=0)

    # Ползунок админа: до какого % потери от стартового баланса сессии
    # игроку разрешено проиграть в реальном режиме, прежде чем реальная
    # игра заблокируется для него на 1 час.
    loss_limit_percent = db.Column(db.Numeric(5, 2), nullable=False, default=30)

    # Кэш курсов валют (JSON {код: сколько единиц за 1 сум}) для отображения
    # эквивалента баланса игроку — см. app/currency.py. Сами ставки/баланс
    # всегда в суммах, курс используется только для показа "на глаз".
    fx_rates_json = db.Column(db.Text, nullable=True)
    fx_rates_updated_at = db.Column(db.DateTime, nullable=True)

    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    @classmethod
    def get(cls):
        row = db.session.get(cls, 1)
        if row is None:
            row = cls(id=1, house_bank=0, loss_limit_percent=30)
            db.session.add(row)
            db.session.commit()
        return row

    @classmethod
    def get_locked(cls):
        """Как get(), но с блокировкой строки (SELECT ... FOR UPDATE) — для
        безопасного изменения house_bank внутри одной транзакции ставки."""
        row = db.session.query(cls).filter_by(id=1).with_for_update().first()
        if row is None:
            row = cls(id=1, house_bank=0, loss_limit_percent=30)
            db.session.add(row)
            db.session.commit()
            row = db.session.query(cls).filter_by(id=1).with_for_update().first()
        return row

    def __repr__(self):
        return f"<CasinoSettings bank={self.house_bank} loss_limit={self.loss_limit_percent}%>"


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
    # карту в профиле. Хранится зашифрованным, как и User.card_number.
    _card_number = db.Column("card_number", db.Text, nullable=True)

    @property
    def card_number(self):
        return decrypt_card_number(self._card_number)

    @card_number.setter
    def card_number(self, value):
        self._card_number = encrypt_card_number(value)

    # Фото/PDF чека, приложенные игроком к заявке на пополнение — для
    # проверки админом, что оплата действительно прошла (необязательно).
    receipt_filename = db.Column(db.String(255), nullable=True)

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
