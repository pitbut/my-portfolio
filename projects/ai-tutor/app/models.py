"""SQLAlchemy-модели модуля «ИИ-репетитор» (см. раздел 8 ТЗ)."""
from datetime import datetime

from app import db


class TimestampMixin:
    """Добавляет created_at/updated_at любой модели."""

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class User(TimestampMixin, db.Model):
    """Ученик (или администратор в будущих версиях — см. раздел 3 ТЗ)."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    email_confirmed = db.Column(db.Boolean, nullable=False, default=False)
    confirmed_at = db.Column(db.DateTime, nullable=True)

    # Текущий выбранный предмет/класс (MVP: один активный курс за раз).
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"), nullable=True)
    grade_id = db.Column(db.Integer, db.ForeignKey("grades.id"), nullable=True)

    # Выбор аватара и голоса при первом входе (раздел 4.1 ТЗ, этап 9.2).
    # avatar_key — ключ из app/avatars.py. voice_name — имя голоса из
    # SpeechSynthesis браузера ученика (выбор голоса возможен только на
    # клиенте — список голосов зависит от браузера/ОС), используется как
    # есть при озвучке через Web Speech API.
    avatar_key = db.Column(db.String(50), nullable=True)
    voice_name = db.Column(db.String(255), nullable=True)

    # Суммарные токены ИИ-API (вход+выход), потраченные на занятия этого
    # ученика — копится в lesson_engine.py после каждого вызова модели.
    # token_limit — необязательный потолок, который админ может задать
    # (см. app/routes/admin.py); null — без ограничения.
    tokens_used = db.Column(db.Integer, nullable=False, default=0)
    token_limit = db.Column(db.Integer, nullable=True)

    subject = db.relationship("Subject")
    grade = db.relationship("Grade")

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

    @property
    def program(self):
        if self.subject_id is None or self.grade_id is None:
            return None
        return Program.query.filter_by(subject_id=self.subject_id, grade_id=self.grade_id).first()

    @property
    def avatar(self):
        from app.avatars import get_avatar

        return get_avatar(self.avatar_key)

    def __repr__(self):
        return f"<User {self.email!r}>"


class Subject(db.Model):
    """Предмет (например «Алгебра»)."""

    __tablename__ = "subjects"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(120), unique=True, nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)

    def __repr__(self):
        return f"<Subject {self.name!r}>"


class Grade(db.Model):
    """Класс/уровень (например «5 класс»)."""

    __tablename__ = "grades"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(120), unique=True, nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    order = db.Column(db.Integer, nullable=False, default=0)  # для сортировки по возрастанию

    def __repr__(self):
        return f"<Grade {self.name!r}>"


class Program(db.Model):
    """Учебная программа: упорядоченный список тем для пары предмет+класс.

    Одна программа переиспользуется всеми учениками на этом уровне (см.
    примечание к Промпту Б в ai-tutor-system-prompt.md)."""

    __tablename__ = "programs"
    __table_args__ = (db.UniqueConstraint("subject_id", "grade_id", name="uq_program_subject_grade"),)

    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"), nullable=False)
    grade_id = db.Column(db.Integer, db.ForeignKey("grades.id"), nullable=False)

    subject = db.relationship("Subject")
    grade = db.relationship("Grade")
    topics = db.relationship(
        "Topic", backref="program", order_by="Topic.order", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Program subject_id={self.subject_id} grade_id={self.grade_id}>"


class Topic(db.Model):
    """Тема программы — MVP: фиксированный список в БД (раздел 9.1 ТЗ)."""

    __tablename__ = "topics"
    __table_args__ = (db.UniqueConstraint("program_id", "order", name="uq_topic_program_order"),)

    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(db.Integer, db.ForeignKey("programs.id"), nullable=False)
    order = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"<Topic #{self.order} {self.title!r}>"


class UserProgress(db.Model):
    """Прогресс ученика по конкретной теме."""

    __tablename__ = "user_progress"
    __table_args__ = (db.UniqueConstraint("user_id", "topic_id", name="uq_progress_user_topic"),)

    STATUS_NOT_STARTED = "not_started"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_COMPLETED = "completed"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    topic_id = db.Column(db.Integer, db.ForeignKey("topics.id"), nullable=False)
    status = db.Column(db.String(20), nullable=False, default=STATUS_NOT_STARTED)
    completed_at = db.Column(db.DateTime, nullable=True)

    topic = db.relationship("Topic")

    def __repr__(self):
        return f"<UserProgress user_id={self.user_id} topic_id={self.topic_id} status={self.status}>"


class Lesson(TimestampMixin, db.Model):
    """Одно занятие — плановое (по программе) или свободное (раздел 4.2/4.3 ТЗ)."""

    __tablename__ = "lessons"

    MODE_PROGRAM = "program"
    MODE_FREE = "free"

    STATUS_ACTIVE = "active"
    STATUS_COMPLETED = "completed"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    topic_id = db.Column(db.Integer, db.ForeignKey("topics.id"), nullable=True)  # null для free-режима
    mode = db.Column(db.String(20), nullable=False, default=MODE_PROGRAM)
    free_topic_text = db.Column(db.String(500), nullable=True)
    status = db.Column(db.String(20), nullable=False, default=STATUS_ACTIVE)

    # Последнее известное служебное состояние из блока STATE ответа модели —
    # определяет, какой элемент интерфейса показать ученику дальше.
    stage = db.Column(db.String(30), nullable=True)
    awaiting = db.Column(db.String(30), nullable=True)
    tasks_required = db.Column(db.Integer, nullable=False, default=3)

    started_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    ended_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship("User")
    topic = db.relationship("Topic")
    messages = db.relationship(
        "LessonMessage", backref="lesson", order_by="LessonMessage.created_at",
        cascade="all, delete-orphan",
    )
    tasks = db.relationship(
        "Task", backref="lesson", order_by="Task.order", cascade="all, delete-orphan"
    )

    @property
    def subject_name(self):
        if self.mode == self.MODE_FREE:
            return "Свободная тема"
        return self.topic.program.subject.name if self.topic else None

    @property
    def topic_title(self):
        return self.free_topic_text if self.mode == self.MODE_FREE else (self.topic.title if self.topic else None)

    def __repr__(self):
        return f"<Lesson #{self.id} user_id={self.user_id} mode={self.mode} status={self.status}>"


class LessonMessage(TimestampMixin, db.Model):
    """Одно сообщение в истории диалога занятия (раздел 8 ТЗ, сущность LessonMessage)."""

    __tablename__ = "lesson_messages"

    SENDER_STUDENT = "student"
    SENDER_TUTOR = "tutor"

    id = db.Column(db.Integer, primary_key=True)
    lesson_id = db.Column(db.Integer, db.ForeignKey("lessons.id"), nullable=False)
    sender = db.Column(db.String(20), nullable=False)

    # Для сообщений ученика — введённый текст. Для сообщений репетитора —
    # распарсенный блок SPEECH (для отображения в чате).
    speech = db.Column(db.Text, nullable=True)
    board_type = db.Column(db.String(20), nullable=True)  # text | formula | steps | diagram | graph
    board_content = db.Column(db.Text, nullable=True)
    photo_url = db.Column(db.String(500), nullable=True)

    # Полный сырой ответ модели (SPEECH+BOARD+STATE) — нужен, чтобы вернуть
    # его назад в историю диалога следующим вызовом ИИ-API как есть, без
    # потери контекста (см. раздел 7 ТЗ: "передавать историю диалога").
    raw_response = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"<LessonMessage #{self.id} lesson_id={self.lesson_id} sender={self.sender}>"


class Task(TimestampMixin, db.Model):
    """Практическое задание, выданное в рамках занятия."""

    __tablename__ = "tasks"

    STATUS_PENDING = "pending"
    STATUS_CORRECT = "correct"
    STATUS_INCORRECT = "incorrect"

    id = db.Column(db.Integer, primary_key=True)
    lesson_id = db.Column(db.Integer, db.ForeignKey("lessons.id"), nullable=False)
    order = db.Column(db.Integer, nullable=False)
    text = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default=STATUS_PENDING)

    submissions = db.relationship(
        "TaskSubmission", backref="task", order_by="TaskSubmission.created_at",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Task #{self.order} lesson_id={self.lesson_id} status={self.status}>"


class TaskSubmission(TimestampMixin, db.Model):
    """Присланное учеником фото решения и результат его проверки."""

    __tablename__ = "task_submissions"

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=False)
    photo_url = db.Column(db.String(500), nullable=True)
    correct = db.Column(db.Boolean, nullable=True)
    feedback = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"<TaskSubmission #{self.id} task_id={self.task_id} correct={self.correct}>"


class ScheduledSession(TimestampMixin, db.Model):
    """Запланированное время следующего занятия (раздел 4.2/9.1 ТЗ)."""

    __tablename__ = "scheduled_sessions"

    STATUS_SCHEDULED = "scheduled"
    STATUS_DONE = "done"
    STATUS_CANCELLED = "cancelled"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey("lessons.id"), nullable=True)
    scheduled_at = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), nullable=False, default=STATUS_SCHEDULED)

    user = db.relationship("User")
    lesson = db.relationship("Lesson")

    def __repr__(self):
        return f"<ScheduledSession #{self.id} user_id={self.user_id} at={self.scheduled_at}>"
