"""Offline-генерация программы тем для новой пары предмет+класс через
Промпт Б (раздел 10 ai-tutor-system-prompt.md), см. app/ai_client.py.

MVP хранит программу как фиксированный список в БД (раздел 9.1 ТЗ) — этот
скрипт заполняет её через ИИ ОДИН РАЗ перед деплоем, а не на лету во время
занятия ученика. Использование:

    python scripts/generate_program.py "Химия" "9 класс" [--curriculum "ФГОС"]

Требует ANTHROPIC_API_KEY в .env. Идемпотентен: если программа для этой
пары предмет+класс уже есть, ничего не создаёт."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app, db  # noqa: E402
from app.ai_client import AIClientError, generate_program  # noqa: E402
from app.models import Grade, Program, Subject, Topic  # noqa: E402
from app.slugify import slugify  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("subject", help='Название предмета, например "Химия"')
    parser.add_argument("grade", help='Класс/уровень, например "9 класс"')
    parser.add_argument("--curriculum", default=None, help="Образовательный стандарт (опционально)")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        subject = Subject.query.filter_by(name=args.subject).first()
        if subject is None:
            subject = Subject(slug=slugify(args.subject, "subject"), name=args.subject)
            db.session.add(subject)
            db.session.flush()

        grade = Grade.query.filter_by(name=args.grade).first()
        if grade is None:
            grade = Grade(slug=slugify(args.grade, "grade"), name=args.grade, order=0)
            db.session.add(grade)
            db.session.flush()

        if Program.query.filter_by(subject_id=subject.id, grade_id=grade.id).first() is not None:
            print(f'Программа "{args.subject}" / "{args.grade}" уже существует — ничего не делаю.')
            return

        try:
            topics = generate_program(args.subject, args.grade, args.curriculum)
        except AIClientError as exc:
            print(f"Ошибка: {exc}", file=sys.stderr)
            sys.exit(1)

        program = Program(subject_id=subject.id, grade_id=grade.id)
        db.session.add(program)
        db.session.flush()

        for item in topics:
            db.session.add(
                Topic(
                    program_id=program.id,
                    order=int(item["order"]),
                    title=item["title"],
                    description=item.get("description"),
                )
            )

        db.session.commit()
        print(f'Готово: программа "{args.subject}" / "{args.grade}" — {len(topics)} тем.')


if __name__ == "__main__":
    main()
