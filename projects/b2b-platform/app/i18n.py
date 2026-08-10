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
    "home.stat_total": {
        "ru": "зарегистрировано всего", "uz_latin": "jami roʻyxatdan oʻtgan", "uz_cyrillic": "жами рўйхатдан ўтган",
        "en": "total registered",
    },
    "home.stat_customer": {
        "ru": "заказчиков", "uz_latin": "buyurtmachilar", "uz_cyrillic": "буюртмачилар", "en": "customers",
    },
    "home.stat_executor": {
        "ru": "исполнителей", "uz_latin": "ijrochilar", "uz_cyrillic": "ижрочилар", "en": "executors",
    },
    "home.stat_constructor": {
        "ru": "конструкторов", "uz_latin": "konstruktorlar", "uz_cyrillic": "конструкторлар", "en": "designers",
    },
    "home.step1_title": {
        "ru": "Регистрация", "uz_latin": "Roʻyxatdan oʻtish", "uz_cyrillic": "Рўйхатдан ўтиш", "en": "Sign up",
    },
    "home.step1_text": {
        "ru": "Заказчик, исполнитель или конструктор регистрируются сами — по email или через Google — и сами заполняют свой профиль.",
        "uz_latin": "Buyurtmachi, ijrochi yoki konstruktor oʻzi roʻyxatdan oʻtadi — email yoki Google orqali — va profilini oʻzi toʻldiradi.",
        "uz_cyrillic": "Буюртмачи, ижрочи ёки конструктор ўзи рўйхатдан ўтади — email ёки Google орқали — ва профилини ўзи тўлдиради.",
        "en": "A customer, executor or designer signs up independently — by email or via Google — and fills in their own profile.",
    },
    "home.step2_title": {
        "ru": "Профиль", "uz_latin": "Profil", "uz_cyrillic": "Профиль", "en": "Profile",
    },
    "home.step2_text": {
        "ru": "Исполнитель указывает станочный парк, допустимые габариты и материалы — это основа автоподбора заказов.",
        "uz_latin": "Ijrochi stanoklar parkini, ruxsat etilgan oʻlchamlarni va materiallarni koʻrsatadi — bu buyurtmalarni avtomatik tanlash asosi.",
        "uz_cyrillic": "Ижрочи станоклар паркини, рухсат этилган ўлчамларни ва материалларни кўрсатади — бу буюртмаларни автоматик танлаш асоси.",
        "en": "The executor specifies their machine fleet, allowed dimensions and materials — the basis for automatic order matching.",
    },
    "home.step3_title": {
        "ru": "Заказы и аукцион", "uz_latin": "Buyurtmalar va auksion", "uz_cyrillic": "Буюртмалар ва аукцион",
        "en": "Orders and bidding",
    },
    "home.step3_text": {
        "ru": "Публикация заявок, автоподбор исполнителей поблизости и аукцион ставок — заказчик сам выбирает победителя.",
        "uz_latin": "Buyurtmalarni joylashtirish, yaqin atrofdagi ijrochilarni avtomatik tanlash va takliflar auksioni — buyurtmachi gʻolibni oʻzi tanlaydi.",
        "uz_cyrillic": "Буюртмаларни жойлаштириш, яқин атрофдаги ижрочиларни автоматик танлаш ва таклифлар аукциони — буюртмачи ғолибни ўзи танлайди.",
        "en": "Posting orders, automatic matching of nearby executors, and a bidding auction — the customer picks the winner themselves.",
    },
    "home.status_note": {
        "ru": "На платформе работают: заказы и автоподбор, карта и геопоиск, отзывы, арбитраж, Telegram-бот и подписки, барахолка станков и инструмента, вакансии и резюме, рынок сырья и материалов, роль «Конструктор», прямые сообщения между пользователями. Подробнее — в",
        "uz_latin": "Platformada ishlaydi: buyurtmalar va avtomatik tanlash, xarita va geo-qidiruv, sharhlar, arbitraj, Telegram-bot va obunalar, stanok va asbob-uskuna bozorchasi, ish oʻrinlari va rezyumelar, xomashyo va materiallar bozori, «Konstruktor» roli, foydalanuvchilar orasidagi toʻgʻridan-toʻgʻri xabarlar. Batafsil —",
        "uz_cyrillic": "Платформада ишлайди: буюртмалар ва автоматик танлаш, харита ва гео-қидирув, шарҳлар, арбитраж, Telegram-бот ва обуналар, станок ва асбоб-ускуна бозорчаси, иш ўринлари ва резюмелар, хомашё ва материаллар бозори, «Конструктор» роли, фойдаланувчилар орасидаги тўғридан-тўғри хабарлар. Батафсил —",
        "en": "The platform supports: orders with auto-matching, map and geo-search, reviews, arbitration, Telegram bot and subscriptions, equipment marketplace, jobs and resumes, raw materials market, the Designer role, and direct messaging between users. More details in the",
    },
    "home.status_note_link": {
        "ru": "техническом задании", "uz_latin": "texnik topshiriqda", "uz_cyrillic": "техник топшириқда",
        "en": "spec document",
    },
    "common.close": {
        "ru": "Закрыть", "uz_latin": "Yopish", "uz_cyrillic": "Ёпиш", "en": "Close",
    },
    "auth.password2": {
        "ru": "Повторите пароль", "uz_latin": "Parolni takrorlang", "uz_cyrillic": "Паролни такрорланг",
        "en": "Repeat password",
    },
    "auth.language": {
        "ru": "Язык интерфейса", "uz_latin": "Interfeys tili", "uz_cyrillic": "Интерфейс тили",
        "en": "Interface language",
    },
    "profile.incomplete_banner": {
        "ru": "Профиль не заполнен — заполните его, чтобы получать заказы и быть видимым в каталоге.",
        "uz_latin": "Profil toʻldirilmagan — buyurtmalar olish uchun uni toʻldiring.",
        "uz_cyrillic": "Профиль тўлдирилмаган — буюртмалар олиш учун уни тўлдиринг.",
        "en": "Profile is incomplete — fill it in to receive orders and appear in the catalog.",
    },
    "error.403_heading": {
        "ru": "Доступ запрещён", "uz_latin": "Kirish taqiqlangan", "uz_cyrillic": "Кириш тақиқланган",
        "en": "Access denied",
    },
    "error.403_message": {
        "ru": "У вас нет прав на просмотр этой страницы — возможно, она относится к другой роли или другому пользователю.",
        "uz_latin": "Sizda bu sahifani koʻrish huquqi yoʻq — ehtimol, u boshqa rolga yoki boshqa foydalanuvchiga tegishli.",
        "uz_cyrillic": "Сизда бу саҳифани кўриш ҳуқуқи йўқ — эҳтимол, у бошқа рольга ёки бошқа фойдаланувчига тегишли.",
        "en": "You don't have permission to view this page — it may belong to a different role or another user.",
    },
    "error.404_heading": {
        "ru": "Страница не найдена", "uz_latin": "Sahifa topilmadi", "uz_cyrillic": "Саҳифа топилмади",
        "en": "Page not found",
    },
    "error.404_message": {
        "ru": "Такой страницы не существует, либо она была удалена.",
        "uz_latin": "Bunday sahifa mavjud emas yoki u oʻchirilgan.",
        "uz_cyrillic": "Бундай саҳифа мавжуд эмас ёки у ўчирилган.",
        "en": "This page doesn't exist, or it has been removed.",
    },
    "error.500_heading": {
        "ru": "Ошибка сервера", "uz_latin": "Server xatosi", "uz_cyrillic": "Сервер хатоси", "en": "Server error",
    },
    "error.500_message": {
        "ru": "Что-то пошло не так на нашей стороне. Мы уже знаем об этом — попробуйте обновить страницу чуть позже.",
        "uz_latin": "Bizning tomondan xatolik yuz berdi. Biz bundan xabardormiz — sahifani biroz keyinroq yangilab koʻring.",
        "uz_cyrillic": "Бизнинг томондан хатолик юз берди. Биз бундан хабардормиз — саҳифани бироз кейинроқ янгилаб кўринг.",
        "en": "Something went wrong on our end. We're already aware — try refreshing the page in a moment.",
    },
    "auth.forgot_password_link": {
        "ru": "Забыли пароль?", "uz_latin": "Parolni unutdingizmi?", "uz_cyrillic": "Паролни унутдингизми?",
        "en": "Forgot password?",
    },
    "auth.no_account": {
        "ru": "Нет аккаунта?", "uz_latin": "Hisobingiz yoʻqmi?", "uz_cyrillic": "Ҳисобингиз йўқми?",
        "en": "No account yet?",
    },
    "auth.have_account": {
        "ru": "Уже есть аккаунт?", "uz_latin": "Hisobingiz bormi?", "uz_cyrillic": "Ҳисобингиз борми?",
        "en": "Already have an account?",
    },
    "auth.who_are_you_title": {
        "ru": "Кто вы на платформе?", "uz_latin": "Siz platformada kimsiz?", "uz_cyrillic": "Сиз платформада кимсиз?",
        "en": "Who are you on the platform?",
    },
    "auth.google_no_role_hint": {
        "ru": "Google не передаёт эту информацию — выберите роль один раз, дальше её можно будет сменить только через поддержку.",
        "uz_latin": "Google bu maʼlumotni yubormaydi — rolni bir marta tanlang, keyin uni faqat qoʻllab-quvvatlash xizmati orqali oʻzgartirish mumkin boʻladi.",
        "uz_cyrillic": "Google бу маълумотни юбормайди — рольни бир марта танланг, кейин уни фақат қўллаб-қувватлаш хизмати орқали ўзгартириш мумкин бўлади.",
        "en": "Google doesn't share this information — choose a role once; after that it can only be changed via support.",
    },
    "common.continue": {
        "ru": "Продолжить", "uz_latin": "Davom etish", "uz_cyrillic": "Давом этиш", "en": "Continue",
    },
    "auth.forgot_password_title": {
        "ru": "Забыли пароль?", "uz_latin": "Parolni unutdingizmi?", "uz_cyrillic": "Паролни унутдингизми?",
        "en": "Forgot password?",
    },
    "auth.forgot_password_hint": {
        "ru": "Укажите email, с которым регистрировались — пришлём ссылку для сброса пароля.",
        "uz_latin": "Roʻyxatdan oʻtgan emailingizni koʻrsating — parolni tiklash uchun havola yuboramiz.",
        "uz_cyrillic": "Рўйхатдан ўтган emailингизни кўрсатинг — паролни тиклаш учун ҳавола юборамиз.",
        "en": "Enter the email you registered with — we'll send a password reset link.",
    },
    "auth.send_link": {
        "ru": "Отправить ссылку", "uz_latin": "Havolani yuborish", "uz_cyrillic": "Ҳаволани юбориш",
        "en": "Send link",
    },
    "auth.back_to_login": {
        "ru": "← Вернуться ко входу", "uz_latin": "← Kirishga qaytish", "uz_cyrillic": "← Киришга қайтиш",
        "en": "← Back to login",
    },
    "auth.reset_password_title": {
        "ru": "Задайте новый пароль", "uz_latin": "Yangi parol oʻrnating", "uz_cyrillic": "Янги парол ўрнатинг",
        "en": "Set a new password",
    },
    "auth.new_password": {
        "ru": "Новый пароль", "uz_latin": "Yangi parol", "uz_cyrillic": "Янги парол", "en": "New password",
    },
    "auth.save_password": {
        "ru": "Сохранить пароль", "uz_latin": "Parolni saqlash", "uz_cyrillic": "Паролни сақлаш",
        "en": "Save password",
    },
    "auth.choose_role_title": {
        "ru": "Выбор роли", "uz_latin": "Rolni tanlash", "uz_cyrillic": "Рольни танлаш", "en": "Choose role",
    },
    "auth.forgot_password_page_title": {
        "ru": "Восстановление пароля", "uz_latin": "Parolni tiklash", "uz_cyrillic": "Паролни тиклаш",
        "en": "Password recovery",
    },
    "auth.reset_password_page_title": {
        "ru": "Новый пароль", "uz_latin": "Yangi parol", "uz_cyrillic": "Янги парол", "en": "New password",
    },
    "error.back_home": {
        "ru": "На главную", "uz_latin": "Bosh sahifaga", "uz_cyrillic": "Бош саҳифага", "en": "Back to home",
    },
}


def translate(key, **kwargs):
    lang = get_current_lang()
    entry = STRINGS.get(key)
    if not entry:
        return key
    text = entry.get(lang, entry["ru"])
    return text.format(**kwargs) if kwargs else text


def register_i18n(app):
    @app.context_processor
    def inject_i18n():
        return {
            "current_lang": get_current_lang(),
            "supported_languages": SUPPORTED_LANGUAGES,
            "language_labels": LANGUAGE_LABELS,
        }

    app.jinja_env.globals["t"] = translate


def get_current_lang():
    if current_user.is_authenticated and current_user.preferred_language in SUPPORTED_LANGUAGES:
        return current_user.preferred_language
    lang = session.get("lang")
    if lang in SUPPORTED_LANGUAGES:
        return lang
    return "ru"
