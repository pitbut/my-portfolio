"""CLI-команды, не предназначенные для публичной регистрации через сайт."""
from datetime import datetime

import click
from werkzeug.security import generate_password_hash


def register_cli(app):
    @app.cli.command("create-admin")
    @click.argument("email")
    @click.argument("password")
    def create_admin(email, password):
        """Создаёт пользователя с ролью admin или повышает существующего.

        Роль admin намеренно недоступна через обычную регистрацию (модуль 1
        ТЗ) — только через эту команду, которую выполняет владелец сервера."""
        from app import db
        from app.models import User

        email = email.strip().lower()
        user = User.query.filter_by(email=email).first()
        if user is None:
            user = User(
                email=email, password_hash=generate_password_hash(password), role="admin",
                email_confirmed=True, confirmed_at=datetime.utcnow(),
            )
            db.session.add(user)
            click.echo(f"Создан новый администратор: {email}")
        else:
            user.role = "admin"
            user.password_hash = generate_password_hash(password)
            click.echo(f"Пользователь {email} назначен администратором.")
        db.session.commit()
