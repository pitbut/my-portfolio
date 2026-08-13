import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from werkzeug.security import generate_password_hash

from app import create_app, db
from app.models import Grade, Program, Subject, Topic, User


@pytest.fixture()
def app():
    app = create_app("testing")

    with app.app_context():
        db.create_all()

        subject = Subject(slug="algebra", name="Алгебра")
        grade = Grade(slug="5-klass", name="5 класс", order=5)
        db.session.add_all([subject, grade])
        db.session.flush()

        program = Program(subject_id=subject.id, grade_id=grade.id)
        db.session.add(program)
        db.session.flush()

        for i in range(1, 4):
            db.session.add(
                Topic(program_id=program.id, order=i, title=f"Тема {i}", description=f"Описание темы {i}")
            )

        db.session.commit()

        yield app

        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def user(app):
    """Создаёт ученика, уже выбравшего предмет/класс, и возвращает его id.

    Возвращается id, а не сам ORM-объект: тесты обычно открывают
    собственный `with app.app_context():` (например, внутри запроса через
    client), и объект, созданный в fixture-контексте, был бы к этому
    моменту detached — используйте `db.session.get(User, user)` внутри своего
    блока app_context."""
    with app.app_context():
        subject = Subject.query.first()
        grade = Grade.query.first()
        u = User(
            name="Тестовый ученик",
            email="student@example.com",
            password_hash=generate_password_hash("password123"),
            email_confirmed=True,
            subject_id=subject.id,
            grade_id=grade.id,
        )
        db.session.add(u)
        db.session.commit()
        return u.id


def login(client, email="student@example.com", password="password123"):
    return client.post("/auth/login", data={"email": email, "password": password}, follow_redirects=True)
