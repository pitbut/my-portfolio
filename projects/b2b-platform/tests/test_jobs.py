from app.models import Notification, ProfessionCategory, Region, Resume, User, Vacancy

from tests.conftest import register


def _login(client, email, password="password123"):
    client.post("/auth/login", data={"email": email, "password": password}, follow_redirects=True)


def test_jobs_require_auth(client):
    resp = client.get("/jobs", follow_redirects=False)
    assert resp.status_code == 302
    assert "auth_required=1" in resp.headers["Location"]


def test_vacancy_lifecycle_and_response_notifies_employer(client):
    register(client, email="employer@example.com", role="executor")
    with client.application.app_context():
        profession_id = ProfessionCategory.query.first().id
        region_id = Region.query.first().id

    resp = client.post(
        "/jobs/new",
        data={
            "title": "Токарь 5 разряда", "profession_category_id": str(profession_id),
            "description": "Работа на ЧПУ, опыт от 3 лет", "employment_type": "full_time",
            "salary_min": "5000000", "salary_max": "8000000", "region_id": str(region_id),
        },
        follow_redirects=True,
    )
    assert "опубликована".encode() in resp.data
    with client.application.app_context():
        vacancy_id = Vacancy.query.first().id
    client.get("/auth/logout")

    register(client, email="candidate@example.com", role="customer")
    resp = client.post(f"/jobs/{vacancy_id}/apply", data={"message": "Готов выйти хоть завтра"}, follow_redirects=True)
    assert "Отклик отправлен".encode() in resp.data

    # повторный отклик не создаёт дубликат
    resp = client.post(f"/jobs/{vacancy_id}/apply", data={"message": "ещё раз"}, follow_redirects=True)
    assert "уже откликались".encode() in resp.data

    with client.application.app_context():
        employer = User.query.filter_by(email="employer@example.com").first()
        notif = Notification.query.filter_by(user_id=employer.id, type="vacancy_response").first()
        assert notif is not None


def test_employer_cannot_apply_to_own_vacancy(client):
    register(client, email="employer2@example.com", role="executor")
    with client.application.app_context():
        profession_id = ProfessionCategory.query.first().id
        region_id = Region.query.first().id
    client.post(
        "/jobs/new",
        data={"title": "Сварщик", "profession_category_id": str(profession_id), "description": "x",
              "employment_type": "shift", "region_id": str(region_id)},
        follow_redirects=True,
    )
    with client.application.app_context():
        vacancy_id = Vacancy.query.first().id

    resp = client.post(f"/jobs/{vacancy_id}/apply", data={}, follow_redirects=True)
    assert "собственную вакансию".encode() in resp.data


def test_resume_create_and_employer_invite_notifies_candidate(client):
    register(client, email="worker@example.com", role="customer")
    with client.application.app_context():
        profession_id = ProfessionCategory.query.first().id
        region_id = Region.query.first().id

    resp = client.post(
        "/resumes/mine",
        data={"profession_category_id": str(profession_id), "experience_years": "5",
              "about": "Работал на ЧПУ 5 лет", "expected_salary": "6000000", "region_id": str(region_id)},
        follow_redirects=True,
    )
    assert "Резюме сохранено".encode() in resp.data
    with client.application.app_context():
        resume_id = Resume.query.first().id
    client.get("/auth/logout")

    register(client, email="employer3@example.com", role="executor")
    resp = client.post(f"/resumes/{resume_id}/invite", data={"message": "Приходите на собеседование"}, follow_redirects=True)
    assert "Приглашение отправлено".encode() in resp.data

    with client.application.app_context():
        worker = User.query.filter_by(email="worker@example.com").first()
        notif = Notification.query.filter_by(user_id=worker.id, type="resume_invite").first()
        assert notif is not None


def test_resume_edit_upserts_single_row_per_user(client):
    register(client, email="worker2@example.com", role="customer")
    with client.application.app_context():
        profession_id = ProfessionCategory.query.first().id
        region_id = Region.query.first().id

    client.post(
        "/resumes/mine",
        data={"profession_category_id": str(profession_id), "about": "первая версия", "region_id": str(region_id)},
        follow_redirects=True,
    )
    client.post(
        "/resumes/mine",
        data={"profession_category_id": str(profession_id), "about": "вторая версия", "region_id": str(region_id)},
        follow_redirects=True,
    )
    with client.application.app_context():
        assert Resume.query.count() == 1
        assert Resume.query.first().about == "вторая версия"
