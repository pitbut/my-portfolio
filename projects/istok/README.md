# 💧 Исток — портал о воде

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/pitbut/my-portfolio)

Flask-приложение о воде во всех смыслах: от священных источников мира до цен на
питьевую воду в магазине. Проект спроектирован с нуля как отдельное расширяемое
серверное приложение (не статичная страница), поэтому для работы требует запуска
Python/Flask-сервера — на GitHub Pages он не откроется напрямую. Для реального
онлайн-доступа проект настроен на деплой в [Render](https://render.com) (см. ниже).

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

## Деплой на Render (реальный онлайн-доступ)

В корне репозитория лежит `render.yaml` (Render Blueprint) — он описывает web-сервис
и бесплатную базу PostgreSQL для `projects/istok` в одном файле, вручную ничего
настраивать не нужно.

1. Зайдите на [render.com](https://render.com) и авторизуйтесь через GitHub (или
   нажмите кнопку «Deploy to Render» в начале этого файла).
2. New → Blueprint → выберите репозиторий `pitbut/my-portfolio`.
3. Render найдёт `render.yaml`, покажет план (веб-сервис `istok` + база `istok-db`,
   оба на бесплатном тарифе) — нажмите **Apply**.
4. Дождитесь первого деплоя (несколько минут). Он сам применит миграции
   (`flask db upgrade`) при старте.
5. Наполните базу данными один раз через вкладку **Shell** сервиса `istok` на Render:
   ```bash
   python seed.py
   ```
   Повторный запуск `seed.py` пересоздаёт таблицы и данные с нуля, поэтому в
   продакшене выполняйте его осознанно, не при каждом деплое.
6. Готово — сервис будет доступен по адресу вида `https://istok.onrender.com`
   (Render покажет точный URL на странице сервиса).

Бесплатный тариф Render «засыпает» после 15 минут без запросов — первое
открытие после простоя может занять 30-60 секунд.

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
