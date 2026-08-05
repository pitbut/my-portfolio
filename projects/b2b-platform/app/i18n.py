"""Лёгкая многоязычность интерфейса: RU / узбекская латиница / узбекская кириллица.

Без Flask-Babel и .po-файлов — просто словарь строк на три языка и функция
t(key), зарегистрированная как Jinja-глобал. Пользовательский контент (текст
заявок, описания цехов) — отдельная история (см. ТЗ, content_translations),
здесь речь только про статичные подписи интерфейса.
"""
from flask import session
from flask_login import current_user

SUPPORTED_LANGUAGES = ("ru", "uz_latin", "uz_cyrillic")

LANGUAGE_LABELS = {
    "ru": "Русский",
    "uz_latin": "Oʻzbekcha (lotin)",
    "uz_cyrillic": "Ўзбекча (кирилл)",
}

STRINGS = {
    "nav.home": {
        "ru": "Главная", "uz_latin": "Bosh sahifa", "uz_cyrillic": "Бош саҳифа",
    },
    "nav.catalog": {
        "ru": "Каталог исполнителей", "uz_latin": "Ijrochilar katalogi", "uz_cyrillic": "Ижрочилар каталоги",
    },
    "nav.login": {
        "ru": "Войти", "uz_latin": "Kirish", "uz_cyrillic": "Кириш",
    },
    "nav.register": {
        "ru": "Регистрация", "uz_latin": "Roʻyxatdan oʻtish", "uz_cyrillic": "Рўйхатдан ўтиш",
    },
    "nav.logout": {
        "ru": "Выйти", "uz_latin": "Chiqish", "uz_cyrillic": "Чиқиш",
    },
    "nav.profile": {
        "ru": "Мой профиль", "uz_latin": "Mening profilim", "uz_cyrillic": "Менинг профилим",
    },
    "home.title": {
        "ru": "Платформа изготовителей и ремонтников оборудования Узбекистана",
        "uz_latin": "Oʻzbekiston uskuna ishlab chiqaruvchi va taʼmirlovchilari platformasi",
        "uz_cyrillic": "Ўзбекистон ускуна ишлаб чиқарувчи ва таъмирловчилари платформаси",
    },
    "home.subtitle": {
        "ru": "Разместите заявку на изготовление или ремонт — систему сама подберёт подходящие цеха и заводы поблизости.",
        "uz_latin": "Ishlab chiqarish yoki taʼmirlash uchun buyurtma joylashtiring — tizim yaqin atrofdagi mos sexlarni oʻzi tanlaydi.",
        "uz_cyrillic": "Ишлаб чиқариш ёки таъмирлаш учун буюртма жойлаштиринг — тизим яқин атрофдаги мос сехларни ўзи танлайди.",
    },
    "home.cta_order": {
        "ru": "Разместить заказ", "uz_latin": "Buyurtma joylashtirish", "uz_cyrillic": "Буюртма жойлаштириш",
    },
    "home.cta_executor": {
        "ru": "Стать исполнителем", "uz_latin": "Ijrochi boʻlish", "uz_cyrillic": "Ижрочи бўлиш",
    },
    "paywall.title": {
        "ru": "Нужна регистрация",
        "uz_latin": "Roʻyxatdan oʻtish talab qilinadi",
        "uz_cyrillic": "Рўйхатдан ўтиш талаб қилинади",
    },
    "paywall.body": {
        "ru": "Чтобы продолжить, войдите в аккаунт или зарегистрируйтесь — это бесплатно и займёт меньше минуты.",
        "uz_latin": "Davom etish uchun hisobingizga kiring yoki roʻyxatdan oʻting — bu bepul va bir daqiqadan kam vaqt oladi.",
        "uz_cyrillic": "Давом этиш учун ҳисобингизга киринг ёки рўйхатдан ўтинг — бу бепул ва бир дақиқадан кам вақт олади.",
    },
    "auth.email": {
        "ru": "Email", "uz_latin": "Email", "uz_cyrillic": "Email",
    },
    "auth.password": {
        "ru": "Пароль", "uz_latin": "Parol", "uz_cyrillic": "Парол",
    },
    "auth.role_customer": {
        "ru": "Я заказчик — ищу исполнителя",
        "uz_latin": "Men buyurtmachiman — ijrochi qidiryapman",
        "uz_cyrillic": "Мен буюртмачиман — ижрочи қидиряпман",
    },
    "auth.role_executor": {
        "ru": "Я исполнитель — цех/завод/мастер",
        "uz_latin": "Men ijrochiman — sex/zavod/usta",
        "uz_cyrillic": "Мен ижрочиман — сех/завод/уста",
    },
    "auth.role_constructor": {
        "ru": "Я конструктор — разрабатываю чертежи на заказ",
        "uz_latin": "Men konstruktorman — buyurtma bilan chizma tayyorlayman",
        "uz_cyrillic": "Мен конструкторман — буюртма билан чизма тайёрлайман",
    },
    "auth.google": {
        "ru": "Войти через Google", "uz_latin": "Google orqali kirish", "uz_cyrillic": "Google орқали кириш",
    },
    "profile.incomplete_banner": {
        "ru": "Профиль не заполнен — заполните его, чтобы получать заказы и быть видимым в каталоге.",
        "uz_latin": "Profil toʻldirilmagan — buyurtmalar olish uchun uni toʻldiring.",
        "uz_cyrillic": "Профиль тўлдирилмаган — буюртмалар олиш учун уни тўлдиринг.",
    },
}


def register_i18n(app):
    @app.context_processor
    def inject_i18n():
        return {
            "current_lang": get_current_lang(),
            "supported_languages": SUPPORTED_LANGUAGES,
            "language_labels": LANGUAGE_LABELS,
        }

    @app.template_global("t")
    def t(key):
        lang = get_current_lang()
        entry = STRINGS.get(key)
        if not entry:
            return key
        return entry.get(lang, entry["ru"])


def get_current_lang():
    if current_user.is_authenticated and current_user.preferred_language in SUPPORTED_LANGUAGES:
        return current_user.preferred_language
    lang = session.get("lang")
    if lang in SUPPORTED_LANGUAGES:
        return lang
    return "ru"
