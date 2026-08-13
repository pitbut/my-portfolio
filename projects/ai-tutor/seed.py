"""Наполняет базу данных предметами, классами и программами тем из CSV в data/.

Запуск: python seed.py

MVP использует фиксированный список тем в БД, а не динамическую генерацию
на каждого ученика (раздел 9.1 ТЗ) — эти CSV и есть тот самый список.
Данные синхронизируются построчно по природному ключу на каждом запуске:
новые строки CSV добавляются, уже существующие не трогаются — можно просто
дописывать темы в data/topics.csv и передеплоивать.

Чтобы сгенерировать данные для НОВОЙ пары предмет+класс через Промпт Б
(раздел 10 ai-tutor-system-prompt.md) вместо ручного заполнения CSV,
используйте scripts/generate_program.py."""
import csv
from pathlib import Path

from app import create_app, db
from app.models import Grade, Program, Subject, Topic

DATA_DIR = Path(__file__).resolve().parent / "data"


def read_csv(filename):
    path = DATA_DIR / filename
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def seed_subjects():
    existing = {row.slug for row in Subject.query.all()}
    added = 0
    for row in read_csv("subjects.csv"):
        slug = row["slug"].strip()
        if slug in existing:
            continue
        db.session.add(Subject(slug=slug, name=row["name"].strip()))
        existing.add(slug)
        added += 1
    return added


def seed_grades():
    existing = {row.slug for row in Grade.query.all()}
    added = 0
    for row in read_csv("grades.csv"):
        slug = row["slug"].strip()
        if slug in existing:
            continue
        db.session.add(Grade(slug=slug, name=row["name"].strip(), order=int(row["order"])))
        existing.add(slug)
        added += 1
    return added


def seed_programs_and_topics():
    subjects_by_slug = {s.slug: s for s in Subject.query.all()}
    grades_by_slug = {g.slug: g for g in Grade.query.all()}

    programs_added = 0
    topics_added = 0

    for row in read_csv("topics.csv"):
        subject = subjects_by_slug.get(row["subject_slug"].strip())
        grade = grades_by_slug.get(row["grade_slug"].strip())
        if subject is None or grade is None:
            continue  # опечатка в CSV — пропускаем строку вместо падения всего сида

        program = Program.query.filter_by(subject_id=subject.id, grade_id=grade.id).first()
        if program is None:
            program = Program(subject_id=subject.id, grade_id=grade.id)
            db.session.add(program)
            db.session.flush()
            programs_added += 1

        order = int(row["order"])
        if Topic.query.filter_by(program_id=program.id, order=order).first() is not None:
            continue

        db.session.add(
            Topic(
                program_id=program.id,
                order=order,
                title=row["title"].strip(),
                description=row.get("description", "").strip() or None,
            )
        )
        topics_added += 1

    return programs_added, topics_added


def seed():
    app = create_app()
    with app.app_context():
        db.create_all()

        subjects_added = seed_subjects()
        db.session.flush()
        grades_added = seed_grades()
        db.session.flush()
        programs_added, topics_added = seed_programs_and_topics()

        db.session.commit()

        print(
            f"Добавлено: {subjects_added} предметов, {grades_added} классов, "
            f"{programs_added} программ, {topics_added} тем."
        )


if __name__ == "__main__":
    seed()
