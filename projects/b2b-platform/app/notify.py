"""Единая нотификационная шина (см. ТЗ, модуль 7, п. «10.4»).

Любое событие отклика (новый матч, ставка, отклик на объявление
барахолки/вакансии, обновление спора) проходит через notify() — она
всегда создаёт запись в notifications (видна в /notifications), а если у
получателя привязан Telegram и на сервере настроен TELEGRAM_BOT_TOKEN,
дублирует её сообщением в Telegram. Пока бот не подключён (нет токена),
работает только in-app канал — это не заглушка, а нормальная деградация
функциональности, как и с Resend/Google выше по коду."""
from datetime import datetime

from app import db
from app.models import Notification


def notify(user, type_, title, body=None, url=None):
    notification = Notification(user_id=user.id, type=type_, title=title, body=body, url=url)
    db.session.add(notification)
    db.session.flush()

    from app.telegram_bot import send_telegram_notification  # локальный импорт — модуль 7
    from app.push import send_push_to_user

    sent = send_telegram_notification(user, title, body, url)
    if sent:
        notification.telegram_sent = True

    send_push_to_user(user, title, body, url)

    return notification


def unread_count(user):
    return Notification.query.filter_by(user_id=user.id, read_at=None).count()
