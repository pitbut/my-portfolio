"""Модуль 9 — вакансии и резюме, отклик в любую сторону."""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user

from app import db
from app.decorators import email_confirmed_required, paywall_required
from app.models import JobResponse, ProfessionCategory, Region, Resume, Vacancy
from app.notify import notify

bp = Blueprint("jobs", __name__)


def _to_int(value):
    value = (value or "").strip()
    return int(value) if value.lstrip("-").isdigit() else None


def _to_decimal(value):
    value = (value or "").strip()
    try:
        return float(value) if value else None
    except ValueError:
        return None


# --- вакансии ---

@bp.route("/jobs")
@paywall_required
def vacancies_index():
    query = Vacancy.query.filter_by(status="active")
    profession_id = request.args.get("profession_id", type=int)
    if profession_id:
        query = query.filter_by(profession_category_id=profession_id)
    region_id = request.args.get("region_id", type=int)
    if region_id:
        query = query.filter_by(region_id=region_id)

    return render_template(
        "jobs/vacancies.html", vacancies=query.order_by(Vacancy.created_at.desc()).all(),
        professions=ProfessionCategory.query.order_by(ProfessionCategory.name_ru).all(),
        regions=Region.query.order_by(Region.name_ru).all(),
    )


@bp.route("/jobs/new", methods=["GET", "POST"])
@paywall_required
@email_confirmed_required
def vacancy_new():
    professions = ProfessionCategory.query.order_by(ProfessionCategory.name_ru).all()
    regions = Region.query.order_by(Region.name_ru).all()

    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        description = (request.form.get("description") or "").strip()
        profession_category_id = _to_int(request.form.get("profession_category_id"))
        region_id = _to_int(request.form.get("region_id"))
        employment_type = request.form.get("employment_type")

        errors = []
        if not title:
            errors.append("Укажите название вакансии.")
        if not description:
            errors.append("Опишите обязанности и требования.")
        if not profession_category_id:
            errors.append("Выберите профессию.")
        if not region_id:
            errors.append("Выберите регион.")
        if employment_type not in ("full_time", "part_time", "shift", "contract"):
            errors.append("Выберите тип занятости.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("jobs/vacancy_form.html", professions=professions, regions=regions, form=request.form)

        vacancy = Vacancy(
            employer_id=current_user.id, profession_category_id=profession_category_id, title=title,
            description=description, employment_type=employment_type,
            salary_min=_to_decimal(request.form.get("salary_min")), salary_max=_to_decimal(request.form.get("salary_max")),
            region_id=region_id, city_id=_to_int(request.form.get("city_id")),
        )
        db.session.add(vacancy)
        db.session.commit()
        flash("Вакансия опубликована.", "success")
        return redirect(url_for("jobs.vacancy_detail", vacancy_id=vacancy.id))

    return render_template("jobs/vacancy_form.html", professions=professions, regions=regions, form={})


@bp.route("/jobs/<int:vacancy_id>")
@paywall_required
def vacancy_detail(vacancy_id):
    vacancy = db.session.get(Vacancy, vacancy_id)
    if vacancy is None:
        abort(404)
    is_owner = vacancy.employer_id == current_user.id
    my_response = None
    if not is_owner:
        my_response = JobResponse.query.filter_by(vacancy_id=vacancy.id, from_user_id=current_user.id).first()
    responses = JobResponse.query.filter_by(vacancy_id=vacancy.id, direction="candidate_to_employer").all() if is_owner else []
    return render_template("jobs/vacancy_detail.html", vacancy=vacancy, is_owner=is_owner, my_response=my_response, responses=responses)


@bp.route("/jobs/<int:vacancy_id>/apply", methods=["POST"])
@paywall_required
@email_confirmed_required
def vacancy_apply(vacancy_id):
    vacancy = db.session.get(Vacancy, vacancy_id)
    if vacancy is None:
        abort(404)
    if vacancy.employer_id == current_user.id:
        flash("Нельзя откликнуться на собственную вакансию.", "error")
        return redirect(url_for("jobs.vacancy_detail", vacancy_id=vacancy.id))
    if JobResponse.query.filter_by(vacancy_id=vacancy.id, from_user_id=current_user.id).first():
        flash("Вы уже откликались на эту вакансию.", "info")
        return redirect(url_for("jobs.vacancy_detail", vacancy_id=vacancy.id))

    message = (request.form.get("message") or "").strip() or None
    db.session.add(JobResponse(
        vacancy_id=vacancy.id, from_user_id=current_user.id, to_user_id=vacancy.employer_id,
        direction="candidate_to_employer", message=message,
    ))
    db.session.commit()

    notify(
        vacancy.employer, "vacancy_response", title=f"Отклик на вакансию «{vacancy.title}»",
        body=message or "Соискатель откликнулся на вашу вакансию.",
        url=url_for("jobs.vacancy_detail", vacancy_id=vacancy.id),
    )
    flash("Отклик отправлен.", "success")
    return redirect(url_for("jobs.vacancy_detail", vacancy_id=vacancy.id))


# --- резюме ---

@bp.route("/resumes")
@paywall_required
def resumes_index():
    query = Resume.query.filter_by(status="active")
    profession_id = request.args.get("profession_id", type=int)
    if profession_id:
        query = query.filter_by(profession_category_id=profession_id)
    region_id = request.args.get("region_id", type=int)
    if region_id:
        query = query.filter_by(region_id=region_id)

    return render_template(
        "jobs/resumes.html", resumes=query.order_by(Resume.created_at.desc()).all(),
        professions=ProfessionCategory.query.order_by(ProfessionCategory.name_ru).all(),
        regions=Region.query.order_by(Region.name_ru).all(),
    )


@bp.route("/resumes/mine", methods=["GET", "POST"])
@paywall_required
def resume_edit():
    resume = Resume.query.filter_by(candidate_id=current_user.id).first()
    professions = ProfessionCategory.query.order_by(ProfessionCategory.name_ru).all()
    regions = Region.query.order_by(Region.name_ru).all()

    if request.method == "POST":
        profession_category_id = _to_int(request.form.get("profession_category_id"))
        region_id = _to_int(request.form.get("region_id"))
        about = (request.form.get("about") or "").strip()

        errors = []
        if not profession_category_id:
            errors.append("Выберите профессию.")
        if not region_id:
            errors.append("Выберите регион.")
        if not about:
            errors.append("Расскажите о своём опыте.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("jobs/resume_form.html", resume=resume, professions=professions, regions=regions)

        if resume is None:
            resume = Resume(candidate_id=current_user.id, profession_category_id=profession_category_id, region_id=region_id, about=about)
            db.session.add(resume)
        else:
            resume.profession_category_id = profession_category_id
            resume.region_id = region_id
            resume.about = about
        resume.experience_years = _to_int(request.form.get("experience_years"))
        resume.expected_salary = _to_decimal(request.form.get("expected_salary"))
        resume.city_id = _to_int(request.form.get("city_id"))
        resume.status = "active"
        db.session.commit()
        flash("Резюме сохранено.", "success")
        return redirect(url_for("jobs.resume_edit"))

    return render_template("jobs/resume_form.html", resume=resume, professions=professions, regions=regions)


@bp.route("/resumes/<int:resume_id>")
@paywall_required
def resume_detail(resume_id):
    resume = db.session.get(Resume, resume_id)
    if resume is None:
        abort(404)
    is_owner = resume.candidate_id == current_user.id
    my_invite = None
    if not is_owner:
        my_invite = JobResponse.query.filter_by(resume_id=resume.id, from_user_id=current_user.id).first()
    invites = JobResponse.query.filter_by(resume_id=resume.id, direction="employer_to_candidate").all() if is_owner else []
    return render_template("jobs/resume_detail.html", resume=resume, is_owner=is_owner, my_invite=my_invite, invites=invites)


@bp.route("/resumes/<int:resume_id>/invite", methods=["POST"])
@paywall_required
@email_confirmed_required
def resume_invite(resume_id):
    resume = db.session.get(Resume, resume_id)
    if resume is None:
        abort(404)
    if resume.candidate_id == current_user.id:
        flash("Нельзя пригласить самого себя.", "error")
        return redirect(url_for("jobs.resume_detail", resume_id=resume.id))
    if JobResponse.query.filter_by(resume_id=resume.id, from_user_id=current_user.id).first():
        flash("Вы уже приглашали этого кандидата.", "info")
        return redirect(url_for("jobs.resume_detail", resume_id=resume.id))

    message = (request.form.get("message") or "").strip() or None
    db.session.add(JobResponse(
        resume_id=resume.id, from_user_id=current_user.id, to_user_id=resume.candidate_id,
        direction="employer_to_candidate", message=message,
    ))
    db.session.commit()

    notify(
        resume.candidate, "resume_invite", title="Работодатель заинтересовался вашим резюме",
        body=message or "Вас пригласили на вакансию.", url=url_for("jobs.resume_detail", resume_id=resume.id),
    )
    flash("Приглашение отправлено.", "success")
    return redirect(url_for("jobs.resume_detail", resume_id=resume.id))
