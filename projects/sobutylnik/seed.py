"""Создаёт таблицы БД и запись настроек по умолчанию. Запуск: python seed.py"""
from app import create_app, db
from app.models import get_settings


def seed():
    app = create_app()
    with app.app_context():
        db.create_all()
        settings = get_settings()
        db.session.commit()
        print(
            f"Готово. app_enabled={settings.app_enabled}, limits_enabled={settings.limits_enabled}, "
            f"default_message_limit={settings.default_message_limit}."
        )


if __name__ == "__main__":
    seed()
