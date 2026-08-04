"""Настройки аккаунта: привязка Telegram, подписка исполнителя (модуль 7)."""
from datetime import datetime, timedelta

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user

from app import db
from app.decorators import paywall_required, role_required
from app.models import Payment, Subscription, SubscriptionPlan, TelegramLink
from app.subscriptions import current_subscription
from app.telegram_bot import bot_deep_link

bp = Blueprint("settings", __name__)


@bp.route("/settings")
@paywall_required
def index():
    deep_link = bot_deep_link(current_user)
    return render_template(
        "settings/index.html", telegram_link=current_user.telegram_link,
        deep_link=deep_link, bot_configured=bool(current_app.config.get("TELEGRAM_BOT_TOKEN")),
    )


@bp.route("/settings/telegram/toggle", methods=["POST"])
@paywall_required
def toggle_telegram():
    link = current_user.telegram_link
    if link is not None:
        link.notifications_enabled = not link.notifications_enabled
        db.session.commit()
    return redirect(url_for("settings.index"))


@bp.route("/settings/telegram/unlink", methods=["POST"])
@paywall_required
def unlink_telegram():
    link = current_user.telegram_link
    if link is not None:
        db.session.delete(link)
        db.session.commit()
        flash("Telegram отвязан.", "info")
    return redirect(url_for("settings.index"))


@bp.route("/subscription", methods=["GET"])
@role_required("executor")
def subscription_page():
    profile = current_user.executor_profile
    sub = current_subscription(profile) if profile else None
    plans = SubscriptionPlan.query.filter(SubscriptionPlan.code != "trial").order_by(SubscriptionPlan.price_monthly_uzs).all()
    pending_payment = None
    if profile:
        pending_sub = Subscription.query.filter_by(executor_id=profile.id, status="pending_payment").order_by(Subscription.started_at.desc()).first()
        pending_payment = pending_sub.payments[-1] if pending_sub and pending_sub.payments else None
    return render_template("settings/subscription.html", subscription=sub, plans=plans, pending_payment=pending_payment)


@bp.route("/subscription/request", methods=["POST"])
@role_required("executor")
def subscription_request():
    profile = current_user.executor_profile
    if profile is None or profile.id is None:
        flash("Сначала заполните профиль исполнителя.", "error")
        return redirect(url_for("profile.executor_edit"))

    plan_code = request.form.get("plan_code")
    provider = request.form.get("provider")
    plan = SubscriptionPlan.query.filter_by(code=plan_code).first()
    if plan is None or provider not in ("payme", "click", "uzcard"):
        flash("Выберите тариф и способ оплаты.", "error")
        return redirect(url_for("settings.subscription_page"))

    subscription = Subscription(executor_id=profile.id, plan_id=plan.id, status="pending_payment", started_at=datetime.utcnow())
    db.session.add(subscription)
    db.session.flush()
    db.session.add(Payment(subscription_id=subscription.id, amount=plan.price_monthly_uzs, provider=provider, status="pending"))
    db.session.commit()

    flash(
        "Заявка на тариф принята. Приём онлайн-оплаты Payme/Click/Uzcard подключается по мере получения "
        "мерчант-аккаунта — сейчас администратор активирует тариф вручную после проверки оплаты вне системы.",
        "info",
    )
    return redirect(url_for("settings.subscription_page"))
