"""Применение ставки на реальные деньги к банку казино и лимиту проигрыша
сессии — общая логика для всех игровых режимов (классика, два кубика,
покер на костях)."""
from datetime import datetime, timedelta
from decimal import Decimal

REAL_PLAY_LOCK_DURATION = timedelta(hours=1)


def check_real_play_allowed(user):
    """Бросает ValueError с причиной, если реальная игра сейчас недоступна
    этому пользователю (лок по лимиту проигрыша или пустой банк казино).
    Возвращает залоченную (FOR UPDATE) строку CasinoSettings при успехе —
    её нужно передать в apply_round_to_house_bank/apply_loss_limit_check."""
    from app.models import CasinoSettings

    if user.real_play_locked_until and user.real_play_locked_until > datetime.utcnow():
        until = user.real_play_locked_until.strftime("%H:%M")
        raise ValueError(
            f"Достигнут лимит проигрыша за сессию. Игра на реальные деньги "
            f"заблокирована до {until} UTC."
        )

    settings = CasinoSettings.get_locked()
    if settings.house_bank <= 0:
        raise ValueError(
            "Банк казино временно пуст. Игра на реальные деньги приостановлена "
            "до пополнения администратором."
        )
    return settings


def check_house_can_cover(settings, bet_amount, potential_payout):
    """Бросает ValueError, если казино не может покрыть возможный выигрыш
    по этой ставке (payout сверх возвращённой ставки) текущим банком."""
    liability = max(potential_payout - bet_amount, Decimal("0.00"))
    if liability > settings.house_bank:
        raise ValueError(
            "Ставка слишком велика для текущего банка казино — уменьшите "
            "сумму или попробуйте позже."
        )


def apply_round_to_house_bank(settings, bet_amount, payout):
    """Обновляет банк казино по итогу раунда: казино забирает ставку и
    выплачивает payout. Никогда не уходит в минус (гарантировано проверкой
    check_house_can_cover перед броском, но клампим на всякий случай)."""
    settings.house_bank += bet_amount - payout
    if settings.house_bank < 0:
        settings.house_bank = Decimal("0.00")


def apply_loss_limit_check(user, settings):
    """После списания баланса проверяет лимит проигрыша за сессию
    (% от session_start_balance) и блокирует реальную игру на 1 час,
    если он достигнут."""
    if not user.session_start_balance or user.session_start_balance <= 0:
        return
    loss_percent = settings.loss_limit_percent
    if not loss_percent or loss_percent <= 0:
        return

    threshold = user.session_start_balance * (Decimal(1) - loss_percent / Decimal(100))
    if user.real_balance <= threshold:
        user.real_play_locked_until = datetime.utcnow() + REAL_PLAY_LOCK_DURATION
