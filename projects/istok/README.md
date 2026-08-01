# 💧 Исток — портал о воде

Flask-приложение о воде во всех смыслах: от священных источников мира до цен на
питьевую воду в магазине. Проект спроектирован с нуля как отдельное расширяемое
серверное приложение (не статичная страница), поэтому для работы требует запуска
Python/Flask-сервера — на GitHub Pages он не откроется напрямую.

## Разделы

- **Библиотека** — книги о воде (название, автор, год, жанр, описание)
- **Статьи** — рубрики, человекочитаемые URL, дата публикации
- **Каталог** — цены на питьевую воду с сортировкой (цена, минерализация, название)
- **Священные источники мира** — локация, координаты, что можно/нельзя, посещаемость, во что верят
- **Оборудование** — фильтры, кулеры, счётчики
- **Опыты с водой** — наука vs мифы
- **Доставка воды** — службы доставки со сроками и ценами

## Архитектура

```
projects/istok/
├── app/
│   ├── __init__.py       # фабрика приложения (create_app)
│   ├── models.py         # SQLAlchemy-модели
│   ├── routes/           # блюпринты: main, sacred, catalog, articles, library
│   ├── templates/        # Jinja2-шаблоны (наследуются от base.html)
│   └── static/           # css/js
├── migrations/           # Flask-Migrate (Alembic)
├── tests/                # pytest — минимум один тест на роут
├── config.py             # конфиги dev/test/prod, переменные окружения
├── seed.py               # наполнение БД тестовыми данными
├── requirements.txt
└── run.py
```

Ключевые архитектурные решения:

- **Application factory + Blueprints** — `create_app()` в `app/__init__.py`,
  разделы подключены как отдельные блюпринты, что позволяет добавлять новые
  разделы без изменения существующих файлов.
- **Модели без БД-специфичных типов** — используются только стандартные типы
  SQLAlchemy, поэтому переключение с SQLite (разработка) на PostgreSQL
  (продакшен) делается через переменную окружения `DATABASE_URL`, без
  изменения `models.py`.
- **Slug + timestamps во всех подходящих моделях** — `SacredSource` и
  `Article` имеют поле `slug` для человекочитаемых URL; все модели
  наследуют `created_at`/`updated_at` через `TimestampMixin`.
- **Миграции с первого коммита** — схема БД меняется через
  `flask db migrate` / `flask db upgrade`, а не руками.

## Быстрый старт

```bash
cd projects/istok
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env            # при необходимости отредактируйте .env

flask db upgrade                # применить миграции (создаст instance/istok.db)
python seed.py                  # наполнить БД тестовыми данными

python run.py                   # http://localhost:5000
```

## Тесты

```bash
pytest
```

## Переключение на PostgreSQL

В `.env` укажите:

```
DATABASE_URL=postgresql://user:password@host:5432/istok
```

и выполните `flask db upgrade` — модели останутся без изменений.

## Добавление нового раздела

1. Модель — в `app/models.py` (используйте `TimestampMixin`, при необходимости `SlugMixin`).
2. Блюпринт — новый файл в `app/routes/`, зарегистрировать в `create_app()`.
3. Шаблоны — папка в `app/templates/`, наследование от `base.html`.
4. Миграция — `flask db migrate -m "..."` → `flask db upgrade`.
5. Тесты — новый файл в `tests/`.
