"""Определение эмоционального состояния ученика по поведенческим сигналам
(раздел 9.3 ТЗ: "Эмоциональный анализ (сначала — по поведенческим сигналам,
камера — опционально позже)"). Работает без вызова ИИ и без камеры — только
на данных, которые у нас и так уже есть (статусы заданий) плюс необязательном
времени бездействия, которое присылает клиент вместе с сообщением.

Камера с определением эмоции по кадру (Промпт В) уже реализована отдельно в
app/ai_client.py:detect_emotion — как опциональное дополнение поверх этой
эвристики, которое можно включить позже, не меняя учебный движок."""
from app.models import Task

CONFUSED_PHRASES = (
    "не понял", "не поняла", "непонятно", "не понимаю",
    "можно ещё раз", "объясни ещё", "объясните ещё", "не совсем понял", "не совсем поняла",
)

# Порог "долгого" бездействия и "очень долгого" — секунды между тем, как
# репетитор показал реплику, и ответом ученика.
BORED_IDLE_SECONDS = 45
TIRED_IDLE_SECONDS = 120


def _consecutive_incorrect(lesson):
    count = 0
    for task in reversed(lesson.tasks):
        if task.status == Task.STATUS_INCORRECT:
            count += 1
        elif task.status == Task.STATUS_CORRECT:
            break
    return count


def infer_emotion_state(lesson, message_text=None, idle_seconds=None):
    """Возвращает одну из меток emotion_state (bored/confused/frustrated/
    tired/engaged) или None, если сигналов недостаточно — тогда учебный
    движок просто не передаёт emotion_state в промпт (раздел 7 ТЗ)."""
    if _consecutive_incorrect(lesson) >= 2:
        return "frustrated"

    if message_text:
        lowered = message_text.lower()
        if any(phrase in lowered for phrase in CONFUSED_PHRASES):
            return "confused"

    if idle_seconds is not None and idle_seconds >= 0:
        if idle_seconds >= TIRED_IDLE_SECONDS:
            return "tired"
        if idle_seconds >= BORED_IDLE_SECONDS:
            return "bored"

    if lesson.tasks and lesson.tasks[-1].status == Task.STATUS_CORRECT:
        return "engaged"

    return None
