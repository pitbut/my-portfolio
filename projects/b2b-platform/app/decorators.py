"""Серверный «жёсткий» paywall (модуль 1 ТЗ).

Важно: блокировка на бэкенде обязательна — фронтенд-модалка сама по себе не
является security-контролем (см. НФТ в ТЗ). Любой protected-роут, вызванный
без активной сессии (напрямую curl'ом, из закладки и т.п.), получает тот же
редирект, что и обычный клик по ссылке в браузере.
"""
from functools import wraps

from flask import abort, flash, redirect, request, url_for
from flask_login import current_user


def paywall_required(view):
    """Требует авторизацию; иначе — редирект на главную с флагом, открывающим
    модальное окно регистрации/входа (не 401-страницу — так задано в ТЗ:
    «главная страница открыта всем, но при попытке перейти в раздел
    срабатывает модальное окно»)."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("main.index", auth_required=1, next=request.full_path))
        return view(*args, **kwargs)

    return wrapped


def email_confirmed_required(view):
    """Требует подтверждённый email — вешается поверх paywall_required/
    role_required на действия, которые создают контент или обязательства
    перед другой стороной (заявка, ставка, сообщение, отзыв, объявление,
    спор, вакансия/резюме и т.п.), а не на весь сайт: смотреть каталог,
    искать и заполнять свою анкету можно и до подтверждения — иначе
    свежезарегистрированный пользователь не смог бы даже донести анкету
    до конца, если письмо задержится."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("main.index", auth_required=1, next=request.full_path))
        if not current_user.email_confirmed:
            flash(
                "Подтвердите email, чтобы выполнить это действие — проверьте почту "
                "или запросите письмо ещё раз в личном кабинете.",
                "error",
            )
            return redirect(request.referrer or url_for("main.index"))
        return view(*args, **kwargs)

    return wrapped


def role_required(role):
    """Требует конкретную бизнес-роль (customer/executor). Применяется поверх
    paywall_required. Если роль ещё не выбрана (первый вход через Google) —
    отправляет на выбор роли.

    Роль admin проходит через любую проверку — администратор должен иметь
    возможность открыть и протестировать любой раздел сайта (модуль 6 ТЗ
    прямо предполагает, что администратор разбирается в происходящем на
    платформе, а не только в очереди споров)."""

    def decorator(view):
        @wraps(view)
        @paywall_required
        def wrapped(*args, **kwargs):
            if current_user.role == "admin":
                return view(*args, **kwargs)
            if current_user.role is None:
                return redirect(url_for("auth.choose_role"))
            if current_user.role != role:
                abort(403)
            return view(*args, **kwargs)

        return wrapped

    return decorator
