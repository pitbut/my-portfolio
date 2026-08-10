"""Лёгкая многоязычность интерфейса: RU / узбекская латиница / узбекская кириллица.

Без Flask-Babel и .po-файлов — просто словарь строк на три языка и функция
t(key), зарегистрированная как Jinja-глобал. Пользовательский контент (текст
заявок, описания цехов) — отдельная история (см. ТЗ, content_translations),
здесь речь только про статичные подписи интерфейса.
"""
from flask import session
from flask_login import current_user

SUPPORTED_LANGUAGES = ("ru", "uz_latin", "uz_cyrillic", "en")

LANGUAGE_LABELS = {
    "ru": "Русский",
    "uz_latin": "Oʻzbekcha (lotin)",
    "uz_cyrillic": "Ўзбекча (кирилл)",
    "en": "English",
}

STRINGS = {
    "nav.home": {
        "ru": "Главная", "uz_latin": "Bosh sahifa", "uz_cyrillic": "Бош саҳифа", "en": "Home",
    },
    "nav.catalog": {
        "ru": "Каталог исполнителей", "uz_latin": "Ijrochilar katalogi", "uz_cyrillic": "Ижрочилар каталоги",
        "en": "Executor catalog",
    },
    "nav.login": {
        "ru": "Войти", "uz_latin": "Kirish", "uz_cyrillic": "Кириш", "en": "Log in",
    },
    "nav.register": {
        "ru": "Регистрация", "uz_latin": "Roʻyxatdan oʻtish", "uz_cyrillic": "Рўйхатдан ўтиш", "en": "Sign up",
    },
    "nav.logout": {
        "ru": "Выйти", "uz_latin": "Chiqish", "uz_cyrillic": "Чиқиш", "en": "Log out",
    },
    "nav.profile": {
        "ru": "Мой профиль", "uz_latin": "Mening profilim", "uz_cyrillic": "Менинг профилим", "en": "My profile",
    },
    "nav.my_orders": {
        "ru": "Мои заказы", "uz_latin": "Mening buyurtmalarim", "uz_cyrillic": "Менинг буюртмаларим",
        "en": "My orders",
    },
    "nav.orders": {
        "ru": "Заказы", "uz_latin": "Buyurtmalar", "uz_cyrillic": "Буюртмалар", "en": "Orders",
    },
    "nav.new_order": {
        "ru": "Новая заявка", "uz_latin": "Yangi buyurtma", "uz_cyrillic": "Янги буюртма", "en": "New order",
    },
    "nav.orders_feed": {
        "ru": "Лента заказов", "uz_latin": "Buyurtmalar lentasi", "uz_cyrillic": "Буюртмалар ленталари",
        "en": "Orders feed",
    },
    "nav.map": {
        "ru": "Карта", "uz_latin": "Xarita", "uz_cyrillic": "Харита", "en": "Map",
    },
    "nav.constructors": {
        "ru": "Конструкторы", "uz_latin": "Konstruktorlar", "uz_cyrillic": "Конструкторлар", "en": "Designers",
    },
    "nav.marketplace": {
        "ru": "Барахолка", "uz_latin": "Bozorcha", "uz_cyrillic": "Бозорча", "en": "Marketplace",
    },
    "nav.jobs": {
        "ru": "Вакансии", "uz_latin": "Ish oʻrinlari", "uz_cyrillic": "Иш ўринлари", "en": "Jobs",
    },
    "nav.materials": {
        "ru": "Материалы", "uz_latin": "Materiallar", "uz_cyrillic": "Материаллар", "en": "Materials",
    },
    "nav.reviews": {
        "ru": "Отзывы", "uz_latin": "Sharhlar", "uz_cyrillic": "Шарҳлар", "en": "Reviews",
    },
    "nav.subscription": {
        "ru": "Подписка", "uz_latin": "Obuna", "uz_cyrillic": "Обуна", "en": "Subscription",
    },
    "nav.admin_disputes": {
        "ru": "Споры (админ)", "uz_latin": "Nizolar (admin)", "uz_cyrillic": "Низолар (админ)",
        "en": "Disputes (admin)",
    },
    "nav.admin_subscriptions": {
        "ru": "Подписки (админ)", "uz_latin": "Obunalar (admin)", "uz_cyrillic": "Обуналар (админ)",
        "en": "Subscriptions (admin)",
    },
    "nav.admin_users": {
        "ru": "Пользователи (админ)", "uz_latin": "Foydalanuvchilar (admin)", "uz_cyrillic": "Фойдаланувчилар (админ)",
        "en": "Users (admin)",
    },
    "nav.settings": {
        "ru": "Настройки", "uz_latin": "Sozlamalar", "uz_cyrillic": "Созламалар", "en": "Settings",
    },
    "nav.search": {
        "ru": "Поиск по сайту", "uz_latin": "Sayt boʻyicha qidiruv", "uz_cyrillic": "Сайт бўйича қидирув",
        "en": "Site search",
    },
    "nav.messages": {
        "ru": "Сообщения", "uz_latin": "Xabarlar", "uz_cyrillic": "Хабарлар", "en": "Messages",
    },
    "nav.notifications": {
        "ru": "Уведомления", "uz_latin": "Bildirishnomalar", "uz_cyrillic": "Билдиришномалар",
        "en": "Notifications",
    },
    "footer.tagline": {
        "ru": "B2B Platform UZ — изготовители и ремонтники оборудования Узбекистана",
        "uz_latin": "B2B Platform UZ — Oʻzbekiston uskuna ishlab chiqaruvchi va taʼmirlovchilari",
        "uz_cyrillic": "B2B Platform UZ — Ўзбекистон ускуна ишлаб чиқарувчи ва таъмирловчилари",
        "en": "B2B Platform UZ — equipment manufacturers and repair shops in Uzbekistan",
    },
    "home.title": {
        "ru": "Платформа изготовителей и ремонтников оборудования Узбекистана",
        "uz_latin": "Oʻzbekiston uskuna ishlab chiqaruvchi va taʼmirlovchilari platformasi",
        "uz_cyrillic": "Ўзбекистон ускуна ишлаб чиқарувчи ва таъмирловчилари платформаси",
        "en": "Platform for equipment manufacturers and repair shops in Uzbekistan",
    },
    "home.subtitle": {
        "ru": "Разместите заявку на изготовление или ремонт — систему сама подберёт подходящие цеха и заводы поблизости.",
        "uz_latin": "Ishlab chiqarish yoki taʼmirlash uchun buyurtma joylashtiring — tizim yaqin atrofdagi mos sexlarni oʻzi tanlaydi.",
        "uz_cyrillic": "Ишлаб чиқариш ёки таъмирлаш учун буюртма жойлаштиринг — тизим яқин атрофдаги мос сехларни ўзи танлайди.",
        "en": "Post a manufacturing or repair order — the system automatically matches suitable shops and factories nearby.",
    },
    "home.cta_order": {
        "ru": "Разместить заказ", "uz_latin": "Buyurtma joylashtirish", "uz_cyrillic": "Буюртма жойлаштириш",
        "en": "Post an order",
    },
    "home.cta_executor": {
        "ru": "Стать исполнителем", "uz_latin": "Ijrochi boʻlish", "uz_cyrillic": "Ижрочи бўлиш",
        "en": "Become an executor",
    },
    "paywall.title": {
        "ru": "Нужна регистрация",
        "uz_latin": "Roʻyxatdan oʻtish talab qilinadi",
        "uz_cyrillic": "Рўйхатдан ўтиш талаб қилинади",
        "en": "Sign-up required",
    },
    "paywall.body": {
        "ru": "Чтобы продолжить, войдите в аккаунт или зарегистрируйтесь — это бесплатно и займёт меньше минуты.",
        "uz_latin": "Davom etish uchun hisobingizga kiring yoki roʻyxatdan oʻting — bu bepul va bir daqiqadan kam vaqt oladi.",
        "uz_cyrillic": "Давом этиш учун ҳисобингизга киринг ёки рўйхатдан ўтинг — бу бепул ва бир дақиқадан кам вақт олади.",
        "en": "To continue, log in or sign up — it's free and takes less than a minute.",
    },
    "auth.email": {
        "ru": "Email", "uz_latin": "Email", "uz_cyrillic": "Email", "en": "Email",
    },
    "auth.password": {
        "ru": "Пароль", "uz_latin": "Parol", "uz_cyrillic": "Парол", "en": "Password",
    },
    "auth.role_customer": {
        "ru": "Я заказчик — ищу исполнителя",
        "uz_latin": "Men buyurtmachiman — ijrochi qidiryapman",
        "uz_cyrillic": "Мен буюртмачиман — ижрочи қидиряпман",
        "en": "I'm a customer — looking for an executor",
    },
    "auth.role_executor": {
        "ru": "Я исполнитель — цех/завод/мастер",
        "uz_latin": "Men ijrochiman — sex/zavod/usta",
        "uz_cyrillic": "Мен ижрочиман — сех/завод/уста",
        "en": "I'm an executor — shop/factory/craftsman",
    },
    "auth.role_constructor": {
        "ru": "Я конструктор — разрабатываю чертежи на заказ",
        "uz_latin": "Men konstruktorman — buyurtma bilan chizma tayyorlayman",
        "uz_cyrillic": "Мен конструкторман — буюртма билан чизма тайёрлайман",
        "en": "I'm a designer — I make drawings to order",
    },
    "auth.google": {
        "ru": "Войти через Google", "uz_latin": "Google orqali kirish", "uz_cyrillic": "Google орқали кириш",
        "en": "Log in with Google",
    },
    "flash.email_not_configured": {
        "ru": "Почтовый сервер на сайте пока не настроен — письмо не отправляется автоматически. Подтвердите email по ссылке:",
        "uz_latin": "Sayt pochta serveri hali sozlanmagan — xat avtomatik yuborilmaydi. Emailni havola orqali tasdiqlang:",
        "uz_cyrillic": "Сайт почта сервери ҳали созланмаган — хат автоматик юборилмайди. Emailни ҳавола орқали тасдиқланг:",
        "en": "The site's mail server isn't configured yet — the email isn't sent automatically. Confirm your email via this link:",
    },
    "flash.google_no_telegram_before": {
        "ru": "Вы вошли через Google — телефон и Telegram у нас ещё не привязаны. Обязательно привяжите Telegram в",
        "uz_latin": "Google orqali kirdingiz — telefon va Telegram hali bogʻlanmagan. Bildirishnomalarni oʻtkazib yubormaslik uchun Telegramni",
        "uz_cyrillic": "Google орқали кирдингиз — телефон ва Telegram ҳали боғланмаган. Билдиришномаларни ўтказиб юбормаслик учун Telegramни",
        "en": "You signed in with Google — your phone and Telegram aren't linked yet. Link Telegram in",
    },
    "flash.google_no_telegram_link": {
        "ru": "настройках", "uz_latin": "sozlamalarda bogʻlang", "uz_cyrillic": "созламаларда боғланг", "en": "settings",
    },
    "flash.google_no_telegram_after": {
        "ru": ", иначе не будете получать уведомления о заказах, откликах и сообщениях.",
        "uz_latin": ", aks holda buyurtmalar, takliflar va xabarlar haqida bildirishnoma olmaysiz.",
        "uz_cyrillic": ", акс ҳолда буюртмалар, таклифлар ва хабарлар ҳақида билдиришнома олмайсиз.",
        "en": ", otherwise you won't receive notifications about orders, bids and messages.",
    },
    "profile.incomplete_banner": {
        "ru": "Профиль не заполнен — заполните его, чтобы получать заказы и быть видимым в каталоге.",
        "uz_latin": "Profil toʻldirilmagan — buyurtmalar olish uchun uni toʻldiring.",
        "uz_cyrillic": "Профиль тўлдирилмаган — буюртмалар олиш учун уни тўлдиринг.",
        "en": "Profile is incomplete — fill it in to receive orders and appear in the catalog.",
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
    def t(key, **kwargs):
        lang = get_current_lang()
        entry = STRINGS.get(key)
        if not entry:
            return key
        text = entry.get(lang, entry["ru"])
        return text.format(**kwargs) if kwargs else text


def get_current_lang():
    if current_user.is_authenticated and current_user.preferred_language in SUPPORTED_LANGUAGES:
        return current_user.preferred_language
    lang = session.get("lang")
    if lang in SUPPORTED_LANGUAGES:
        return lang
    return "ru"
