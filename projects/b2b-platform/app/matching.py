"""Модуль 2 — логика автоматического подбора исполнителей под заказ.

Реализует формулу из ТЗ (обязательные фильтры + взвешенный скоринг), но без
фоновой очереди — запускается синхронно в момент публикации заказа. Для
объёмов, на которые рассчитан MVP, это приемлемо; вынос в фоновую задачу
(Celery/RQ) — прямой перенос run_matching() в отдельного воркера без
изменения самой логики."""
from datetime import datetime

from app import db
from app.geo import haversine_km
from app.models import ExecutorCapability, ExecutorProfile, OrderMatch
from app.notify import notify
from app.subscriptions import has_active_subscription

TOP_N_CANDIDATES = 20


def _fits_dimensions(order, capability):
    checks = [
        (order.dimensions_length_mm, capability.max_length_mm),
        (order.dimensions_diameter_mm, capability.max_diameter_mm),
        (order.dimensions_width_mm, capability.max_width_mm),
        (order.dimensions_height_mm, capability.max_height_mm),
    ]
    for order_value, executor_max in checks:
        if order_value is not None and executor_max is not None and order_value > executor_max:
            return False
    if order.weight_kg is not None and capability.max_weight_kg is not None and order.weight_kg > capability.max_weight_kg:
        return False
    return True


def _score(order, executor, capability, distance_km):
    score = 0.0
    if order.material_id is not None and any(m.id == order.material_id for m in capability.materials):
        score += 20.0
    if distance_km is None:
        score += 10.0  # нейтральный балл, если у одной из сторон не указаны координаты
    else:
        score += max(0.0, 30.0 - distance_km / 10.0)
    if executor.region_id == order.region_id:
        score += 15.0
    if executor.rating_avg is not None:
        score += float(executor.rating_avg) * 2
    else:
        score += 5.0
    return round(score, 2)


def find_candidates(order):
    """Возвращает список (executor_profile, score, distance_km), отсортированный
    по убыванию score — используется и для реального матчинга, и в тестах."""
    capabilities = (
        ExecutorCapability.query
        .join(ExecutorProfile, ExecutorCapability.executor_id == ExecutorProfile.id)
        .filter(ExecutorCapability.service_categories.any(id=order.service_category_id))
        .all()
    )

    results = []
    for capability in capabilities:
        executor = capability.executor
        if executor.user.role != "executor":  # переключился на другую роль в настройках — из матчинга выбывает
            continue
        if not executor.equipment:  # не считается «опубликованным» без станочного парка
            continue
        if not has_active_subscription(executor):  # см. ТЗ, модуль 2: без подписки в матчинг не попадает
            continue
        if not _fits_dimensions(order, capability):
            continue

        distance_km = None
        if order.latitude is not None and order.longitude is not None and executor.latitude is not None and executor.longitude is not None:
            distance_km = haversine_km(order.latitude, order.longitude, executor.latitude, executor.longitude)
            if executor.service_radius_km and distance_km > executor.service_radius_km:
                continue

        score = _score(order, executor, capability, distance_km)
        results.append((executor, score, distance_km))

    results.sort(key=lambda item: item[1], reverse=True)
    return results[:TOP_N_CANDIDATES]


def run_matching(order):
    """Находит кандидатов, создаёт order_matches и уведомляет исполнителей.
    Идемпотентна: повторный вызов не дублирует уже уведомлённых исполнителей."""
    already_matched_ids = {m.executor_id for m in order.matches}

    candidates = find_candidates(order)
    created = 0
    for executor, score, distance_km in candidates:
        if executor.id in already_matched_ids:
            continue
        match = OrderMatch(
            order_id=order.id, executor_id=executor.id, match_score=score,
            distance_km=distance_km, notified_at=datetime.utcnow(),
        )
        db.session.add(match)
        created += 1

        notify(
            executor.user, "new_order_match",
            title=f"Новый заказ: {order.title}",
            body=order.description[:200],
            url=f"/orders/{order.id}",
        )

    db.session.commit()
    return created
