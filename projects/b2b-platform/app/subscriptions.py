"""Модуль 7 — подписки исполнителей.

Онлайн-эквайринг (Payme/Click/Uzcard) требует реального мерчант-аккаунта,
которого у платформы пока нет — see README. До его подключения заявки на
платный тариф обрабатываются администратором вручную (тот же принцип, что
и RESEND_API_KEY/GOOGLE_CLIENT_ID выше по коду: честная деградация, а не
притворная имитация оплаты). Бесплатный пробный период включается сам —
это уже полноценная работающая механика, не заглушка."""
from datetime import datetime, timedelta

from app import db
from app.models import Subscription, SubscriptionPlan

TRIAL_DAYS = 30


def get_or_seed_trial_plan():
    plan = SubscriptionPlan.query.filter_by(code="trial").first()
    if plan is None:
        plan = SubscriptionPlan(
            code="trial", title="Пробный период", price_monthly_uzs=0,
            max_bids_per_month=10, telegram_alert_delay_minutes=120, catalog_priority=0,
        )
        db.session.add(plan)
        db.session.flush()
    return plan


def current_subscription(executor):
    """Действующая подписка исполнителя (последняя по expires_at) или None."""
    subs = [s for s in executor.subscriptions if s.is_active_now]
    if not subs:
        return None
    return max(subs, key=lambda s: s.expires_at or datetime.max)


def has_active_subscription(executor):
    return current_subscription(executor) is not None


def start_trial_if_needed(executor):
    """Выдаёт бесплатный пробный период при первом полном заполнении профиля
    (модуль 3) — исполнитель не должен ждать ручных действий администратора,
    чтобы начать получать заказы."""
    if executor.subscriptions:
        return None
    plan = get_or_seed_trial_plan()
    subscription = Subscription(
        executor_id=executor.id, plan_id=plan.id, status="trialing",
        started_at=datetime.utcnow(), expires_at=datetime.utcnow() + timedelta(days=TRIAL_DAYS),
    )
    db.session.add(subscription)
    db.session.commit()
    return subscription
