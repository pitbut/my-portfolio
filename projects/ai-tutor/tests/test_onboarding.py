from app import db
from app.models import Program, User, UserProgress
from tests.conftest import login


def test_choose_subject_sets_user_program(app, client):
    with app.app_context():
        client.post(
            "/auth/register",
            data={
                "name": "Боря",
                "email": "borya@example.com",
                "password": "password123",
                "password2": "password123",
            },
        )
        program = Program.query.first()

        response = client.post("/onboarding/subject", data={"program_id": program.id})
        assert response.status_code == 302
        assert "/onboarding/known-topics" in response.headers["Location"]

        u = User.query.filter_by(email="borya@example.com").first()
        assert u.subject_id == program.subject_id
        assert u.grade_id == program.grade_id


def test_known_topics_marks_progress_completed(app, client, user):
    with app.app_context():
        login(client)
        u = db.session.get(User, user)
        program = u.program
        first_topic = program.topics[0]

        response = client.post(
            "/onboarding/known-topics", data={"known_topic_id": str(first_topic.id)}
        )
        assert response.status_code == 302

        progress = UserProgress.query.filter_by(user_id=u.id, topic_id=first_topic.id).first()
        assert progress.status == UserProgress.STATUS_COMPLETED
