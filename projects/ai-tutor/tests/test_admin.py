from app import db
from app.models import Grade, Lesson, Program, ScheduledSession, Subject, Topic, User, UserProgress


def admin_login(app, client):
    with app.app_context():
        password = app.config["ADMIN_PASSWORD"]
    return client.post("/admin/login", data={"password": password})


def test_protected_route_redirects_to_login(client):
    response = client.get("/admin/programs")
    assert response.status_code == 302
    assert "/admin/login" in response.headers["Location"]


def test_wrong_password_rejected(client):
    response = client.post("/admin/login", data={"password": "definitely-wrong"})
    assert response.status_code == 200
    response = client.get("/admin/programs")
    assert response.status_code == 302


def test_correct_password_grants_access(app, client):
    response = admin_login(app, client)
    assert response.status_code == 302
    assert "/admin/programs" in response.headers["Location"]

    response = client.get("/admin/programs")
    assert response.status_code == 200


def test_admin_can_add_subject_grade_and_program(app, client):
    admin_login(app, client)

    client.post("/admin/programs", data={"form": "new_subject", "subject_name": "Химия"})
    client.post("/admin/programs", data={"form": "new_grade", "grade_name": "9 класс", "grade_order": "9"})

    with app.app_context():
        subject = Subject.query.filter_by(name="Химия").first()
        grade = Grade.query.filter_by(name="9 класс").first()
        assert subject is not None
        assert grade is not None

        response = client.post(
            "/admin/programs", data={"form": "new_program", "subject_id": subject.id, "grade_id": grade.id}
        )
        assert response.status_code == 302
        program = Program.query.filter_by(subject_id=subject.id, grade_id=grade.id).first()
        assert program is not None
        assert f"/admin/programs/{program.id}/topics" in response.headers["Location"]


def test_admin_can_add_and_delete_topic(app, client):
    admin_login(app, client)

    with app.app_context():
        program = Program.query.first()
        program_id = program.id

    response = client.post(
        f"/admin/programs/{program_id}/topics",
        data={"title": "Новая тема", "description": "Описание", "order": "99"},
    )
    assert response.status_code == 302

    with app.app_context():
        topic = Topic.query.filter_by(program_id=program_id, title="Новая тема").first()
        assert topic is not None
        topic_id = topic.id

    response = client.post(f"/admin/topics/{topic_id}/delete")
    assert response.status_code == 302

    with app.app_context():
        assert db.session.get(Topic, topic_id) is None


def test_students_page_renders(app, client, user):
    admin_login(app, client)
    response = client.get("/admin/students")
    assert response.status_code == 200


def test_students_page_shows_stats(app, client, user):
    admin_login(app, client)
    response = client.get("/admin/students")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Токены" in html or "Зарегистрировано" in html


def test_student_detail_page_renders(app, client, user):
    admin_login(app, client)
    response = client.get(f"/admin/students/{user}")
    assert response.status_code == 200


def test_student_detail_requires_admin(client, user):
    response = client.get(f"/admin/students/{user}")
    assert response.status_code == 302
    assert "/admin/login" in response.headers["Location"]


def test_admin_can_set_and_clear_token_limit(app, client, user):
    admin_login(app, client)

    response = client.post(f"/admin/students/{user}/limit", data={"token_limit": "5000"})
    assert response.status_code == 302
    with app.app_context():
        assert db.session.get(User, user).token_limit == 5000

    response = client.post(f"/admin/students/{user}/limit", data={"token_limit": ""})
    assert response.status_code == 302
    with app.app_context():
        assert db.session.get(User, user).token_limit is None


def test_admin_can_delete_student_and_cascades(app, client, user):
    admin_login(app, client)

    with app.app_context():
        u = db.session.get(User, user)
        lesson = Lesson(user_id=u.id, mode=Lesson.MODE_FREE, free_topic_text="Тест")
        db.session.add(lesson)
        db.session.add(UserProgress(user_id=u.id, topic_id=Topic.query.first().id))
        db.session.add(ScheduledSession(user_id=u.id, scheduled_at=lesson.started_at))
        db.session.commit()
        lesson_id = lesson.id

    response = client.post(f"/admin/students/{user}/delete")
    assert response.status_code == 302

    with app.app_context():
        assert db.session.get(User, user) is None
        assert db.session.get(Lesson, lesson_id) is None
        assert UserProgress.query.filter_by(user_id=user).count() == 0
        assert ScheduledSession.query.filter_by(user_id=user).count() == 0


def test_admin_can_email_student(app, client, user):
    admin_login(app, client)
    response = client.post(
        f"/admin/students/{user}/email",
        data={"subject": "Привет", "body": "Как дела?"},
    )
    assert response.status_code == 302  # без RESEND_API_KEY в тестах уйдёт в лог, не упадёт


def test_generate_topics_shows_preview_without_saving(app, client, monkeypatch):
    admin_login(app, client)

    monkeypatch.setattr(
        "app.routes.admin.generate_program",
        lambda subject, grade, curriculum=None: [
            {"order": 1, "title": "Сгенерированная тема 1", "description": "Описание 1"},
            {"order": 2, "title": "Сгенерированная тема 2", "description": "Описание 2"},
        ],
    )

    with app.app_context():
        program_id = Program.query.first().id

    response = client.post(f"/admin/programs/{program_id}/generate")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Сгенерированная тема 1" in html
    assert "Сгенерированная тема 2" in html

    with app.app_context():
        # фикстура app уже сажает 3 темы в первую программу — счётчик не должен
        # вырасти, раз это только предпросмотр, а не сохранение
        assert Topic.query.filter_by(program_id=program_id).count() == 3


def test_generate_topics_handles_ai_error(app, client, monkeypatch):
    from app.ai_client import AIClientError

    admin_login(app, client)

    def _raise(subject, grade, curriculum=None):
        raise AIClientError("ключ не настроен")

    monkeypatch.setattr("app.routes.admin.generate_program", _raise)

    with app.app_context():
        program_id = Program.query.first().id

    response = client.post(f"/admin/programs/{program_id}/generate")
    assert response.status_code == 302
    assert f"/admin/programs/{program_id}/topics" in response.headers["Location"]


def test_generate_topics_save_persists_only_checked_rows(app, client):
    admin_login(app, client)

    with app.app_context():
        program_id = Program.query.first().id

    response = client.post(
        f"/admin/programs/{program_id}/generate/save",
        data={
            # фикстура app уже сажает темы с order 1-3 в эту программу —
            # берём заведомо свободные номера, чтобы не словить UNIQUE-конфликт
            "order": ["10", "11"],
            "title": ["Принятая тема", "Отклонённая тема"],
            "description": ["Описание", "Описание"],
            "include": ["0"],  # только первая тема отмечена
        },
    )
    assert response.status_code == 302

    with app.app_context():
        topics = Topic.query.filter_by(program_id=program_id).all()
        titles = {t.title for t in topics}
        assert "Принятая тема" in titles
        assert "Отклонённая тема" not in titles


def test_generate_topics_save_avoids_order_collision_with_existing_topics(app, client):
    """Регрессия: у программы уже есть темы 1-3 (фикстура app). Раньше форма
    предпросмотра предлагала номера от ИИ, тоже начинающиеся с 1 — сохранение
    падало с IntegrityError по (program_id, order). Теперь конфликтующий
    номер должен тихо переехать на первый свободный, а не уронить запрос."""
    admin_login(app, client)

    with app.app_context():
        program_id = Program.query.first().id
        existing_orders = {t.order for t in Topic.query.filter_by(program_id=program_id).all()}
        assert 1 in existing_orders  # подтверждаем, что коллизия действительно возможна

    response = client.post(
        f"/admin/programs/{program_id}/generate/save",
        data={
            "order": ["1"],  # намеренно конфликтующий номер
            "title": ["Тема с конфликтующим номером"],
            "description": ["..."],
            "include": ["0"],
        },
    )
    assert response.status_code == 302

    with app.app_context():
        topic = Topic.query.filter_by(program_id=program_id, title="Тема с конфликтующим номером").first()
        assert topic is not None
        assert topic.order not in existing_orders
