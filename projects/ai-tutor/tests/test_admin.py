from app import db
from app.models import Grade, Program, Subject, Topic


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
