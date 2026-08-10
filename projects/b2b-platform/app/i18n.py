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
    "profile.customer_title": {
        "ru": "Профиль заказчика", "uz_latin": "Buyurtmachi profili", "uz_cyrillic": "Буюртмачи профили",
        "en": "Customer profile",
    },
    "profile.fill_hint": {
        "ru": "Заполните карточку сами — это займёт пару минут. Обязательные поля отмечены *.",
        "uz_latin": "Kartochkani oʻzingiz toʻldiring — bu bir necha daqiqa oladi. Majburiy maydonlar * bilan belgilangan.",
        "uz_cyrillic": "Карточкани ўзингиз тўлдиринг — бу бир неча дақиқа олади. Мажбурий майдонлар * билан белгиланган.",
        "en": "Fill in the form yourself — it takes a couple of minutes. Required fields are marked *.",
    },
    "profile.complete_badge": {
        "ru": "Профиль заполнен", "uz_latin": "Profil toʻldirilgan", "uz_cyrillic": "Профиль тўлдирилган",
        "en": "Profile complete",
    },
    "profile.incomplete_badge": {
        "ru": "Профиль не заполнен", "uz_latin": "Profil toʻldirilmagan", "uz_cyrillic": "Профиль тўлдирилмаган",
        "en": "Profile incomplete",
    },
    "profile.who_are_you": {
        "ru": "Кто вы? *", "uz_latin": "Siz kimsiz? *", "uz_cyrillic": "Сиз кимсиз? *", "en": "Who are you? *",
    },
    "profile.individual": {
        "ru": "Физическое лицо", "uz_latin": "Jismoniy shaxs", "uz_cyrillic": "Жисмоний шахс",
        "en": "Individual",
    },
    "profile.company": {
        "ru": "Компания (юр. лицо)", "uz_latin": "Kompaniya (yuridik shaxs)", "uz_cyrillic": "Компания (юридик шахс)",
        "en": "Company (legal entity)",
    },
    "profile.company_or_name": {
        "ru": "Название компании / ФИО *", "uz_latin": "Kompaniya nomi / F.I.Sh. *",
        "uz_cyrillic": "Компания номи / Ф.И.Ш. *", "en": "Company name / Full name *",
    },
    "profile.phone": {
        "ru": "Контактный телефон", "uz_latin": "Aloqa uchun telefon", "uz_cyrillic": "Алоқа учун телефон",
        "en": "Contact phone",
    },
    "profile.stir_inn": {
        "ru": "ИНН / СТИР (если компания)", "uz_latin": "STIR (agar kompaniya boʻlsa)",
        "uz_cyrillic": "СТИР (агар компания бўлса)", "en": "Tax ID (if a company)",
    },
    "profile.region": {
        "ru": "Регион *", "uz_latin": "Viloyat *", "uz_cyrillic": "Вилоят *", "en": "Region *",
    },
    "profile.select_placeholder": {
        "ru": "— выберите —", "uz_latin": "— tanlang —", "uz_cyrillic": "— танланг —", "en": "— select —",
    },
    "profile.city": {
        "ru": "Город", "uz_latin": "Shahar", "uz_cyrillic": "Шаҳар", "en": "City",
    },
    "profile.city_placeholder": {
        "ru": "— сначала выберите регион —", "uz_latin": "— avval viloyatni tanlang —",
        "uz_cyrillic": "— аввал вилоятни танланг —", "en": "— select region first —",
    },
    "profile.object_address": {
        "ru": "Адрес объекта *", "uz_latin": "Obyekt manzili *", "uz_cyrillic": "Объект манзили *",
        "en": "Site address *",
    },
    "profile.map_hint": {
        "ru": "Уточните точку на карте (нажмите на карту, чтобы поставить/передвинуть маркер)",
        "uz_latin": "Xaritada nuqtani aniqlashtiring (belgini qoʻyish/koʻchirish uchun xaritaga bosing)",
        "uz_cyrillic": "Харитада нуқтани аниқлаштиринг (белгини қўйиш/кўчириш учун харитага босинг)",
        "en": "Refine the point on the map (click the map to place/move the marker)",
    },
    "profile.save": {
        "ru": "Сохранить профиль", "uz_latin": "Profilni saqlash", "uz_cyrillic": "Профилни сақлаш",
        "en": "Save profile",
    },
    "profile.executor_title": {
        "ru": "Профиль исполнителя", "uz_latin": "Ijrochi profili", "uz_cyrillic": "Ижрочи профили",
        "en": "Executor profile",
    },
    "profile.executor_complete_badge": {
        "ru": "Профиль заполнен — участвует в подборе заказов",
        "uz_latin": "Profil toʻldirilgan — buyurtmalarni tanlashda ishtirok etadi",
        "uz_cyrillic": "Профиль тўлдирилган — буюртмаларни танлашда иштирок этади",
        "en": "Profile complete — participates in order matching",
    },
    "profile.executor_incomplete_badge": {
        "ru": "Профиль не заполнен — пока не участвует в подборе заказов",
        "uz_latin": "Profil toʻldirilmagan — hozircha buyurtmalarni tanlashda ishtirok etmaydi",
        "uz_cyrillic": "Профиль тўлдирилмаган — ҳозирча буюртмаларни танлашда иштирок этмайди",
        "en": "Profile incomplete — doesn't participate in order matching yet",
    },
    "profile.checklist1": {
        "ru": "1. Основная информация (тип, название, регион, адрес)",
        "uz_latin": "1. Asosiy maʼlumot (turi, nomi, viloyat, manzil)",
        "uz_cyrillic": "1. Асосий маълумот (тури, номи, вилоят, манзил)",
        "en": "1. Basic information (type, name, region, address)",
    },
    "profile.checklist2": {
        "ru": "2. Станочный парк — добавлена хотя бы одна единица оборудования",
        "uz_latin": "2. Stanoklar parki — kamida bitta uskuna qoʻshilgan",
        "uz_cyrillic": "2. Станоклар парки — камида битта ускуна қўшилган",
        "en": "2. Machine fleet — at least one piece of equipment added",
    },
    "profile.checklist3": {
        "ru": "3. Выбрана хотя бы одна категория услуг ниже",
        "uz_latin": "3. Quyida kamida bitta xizmat toifasi tanlangan",
        "uz_cyrillic": "3. Қуйида камида битта хизмат тоифаси танланган",
        "en": "3. At least one service category selected below",
    },
    "profile.section_basic_info": {
        "ru": "1. Основная информация", "uz_latin": "1. Asosiy maʼlumot", "uz_cyrillic": "1. Асосий маълумот",
        "en": "1. Basic information",
    },
    "profile.org_type": {
        "ru": "Тип организации *", "uz_latin": "Tashkilot turi *", "uz_cyrillic": "Ташкилот тури *",
        "en": "Organization type *",
    },
    "profile.org_master": {
        "ru": "Мастер (частное лицо/ИП)", "uz_latin": "Usta (jismoniy shaxs/YaTT)",
        "uz_cyrillic": "Уста (жисмоний шахс/ЯТТ)", "en": "Craftsman (individual/sole proprietor)",
    },
    "profile.org_tsekh": {
        "ru": "Цех", "uz_latin": "Sex", "uz_cyrillic": "Сех", "en": "Shop",
    },
    "profile.org_zavod": {
        "ru": "Завод", "uz_latin": "Zavod", "uz_cyrillic": "Завод", "en": "Factory",
    },
    "profile.shop_name": {
        "ru": "Название цеха/завода или ФИО мастера *", "uz_latin": "Sex/zavod nomi yoki usta F.I.Sh. *",
        "uz_cyrillic": "Сех/завод номи ёки уста Ф.И.Ш. *", "en": "Shop/factory name or craftsman's full name *",
    },
    "profile.description": {
        "ru": "Описание", "uz_latin": "Tavsif", "uz_cyrillic": "Тавсиф", "en": "Description",
    },
    "profile.description_placeholder": {
        "ru": "Чем занимаетесь, какой опыт, какие работы выполняете",
        "uz_latin": "Nima bilan shugʻullanasiz, tajribangiz, qanday ishlarni bajarasiz",
        "uz_cyrillic": "Нима билан шуғулланасиз, тажрибангиз, қандай ишларни бажарасиз",
        "en": "What you do, your experience, what work you perform",
    },
    "profile.stir_inn_short": {
        "ru": "ИНН / СТИР", "uz_latin": "STIR", "uz_cyrillic": "СТИР", "en": "Tax ID",
    },
    "profile.shop_address": {
        "ru": "Адрес цеха/завода *", "uz_latin": "Sex/zavod manzili *", "uz_cyrillic": "Сех/завод манзили *",
        "en": "Shop/factory address *",
    },
    "profile.find_on_map": {
        "ru": "Найти на карте по адресу", "uz_latin": "Manzil boʻyicha xaritadan topish",
        "uz_cyrillic": "Манзил бўйича харитадан топиш", "en": "Find on map by address",
    },
    "profile.map_hint_geocode": {
        "ru": "Уточните точку на карте (или поправьте маркер вручную — геокодер по адресу иногда ошибается)",
        "uz_latin": "Xaritada nuqtani aniqlashtiring (yoki belgini qoʻlda toʻgʻrilang — manzil boʻyicha geokoder baʼzan xato qiladi)",
        "uz_cyrillic": "Харитада нуқтани аниқлаштиринг (ёки белгини қўлда тўғриланг — манзил бўйича геокодер баъзан хато қилади)",
        "en": "Refine the point on the map (or adjust the marker manually — the address geocoder is sometimes wrong)",
    },
    "profile.service_radius": {
        "ru": "Готовность выезжать на ремонт в радиусе, км", "uz_latin": "Taʼmirlashga borish radiusi, km",
        "uz_cyrillic": "Таъмирлашга бориш радиуси, км", "en": "Willing to travel for repairs, radius in km",
    },
    "profile.has_design_engineer": {
        "ru": "Есть конструктор в штате (можем сами разработать чертёж)",
        "uz_latin": "Shtatda konstruktor bor (chizmani oʻzimiz tayyorlay olamiz)",
        "uz_cyrillic": "Штатда конструктор бор (чизмани ўзимиз тайёрлай оламиз)",
        "en": "We have an in-house designer (we can prepare drawings ourselves)",
    },
    "profile.payment_methods_legend": {
        "ru": "Способ оплаты, который принимаете (необязательно)",
        "uz_latin": "Qabul qiladigan toʻlov usuli (ixtiyoriy)",
        "uz_cyrillic": "Қабул қиладиган тўлов усули (ихтиёрий)",
        "en": "Payment methods you accept (optional)",
    },
    "profile.workload_label": {
        "ru": "Загруженность сейчас, 1–10 (необязательно; 1 — свободен, 10 — полностью занят)",
        "uz_latin": "Hozirgi yuklama, 1–10 (ixtiyoriy; 1 — boʻsh, 10 — toʻliq band)",
        "uz_cyrillic": "Ҳозирги юклама, 1–10 (ихтиёрий; 1 — бўш, 10 — тўлиқ банд)",
        "en": "Current workload, 1–10 (optional; 1 — free, 10 — fully booked)",
    },
    "profile.save_basic_info": {
        "ru": "Сохранить основную информацию", "uz_latin": "Asosiy maʼlumotni saqlash",
        "uz_cyrillic": "Асосий маълумотни сақлаш", "en": "Save basic information",
    },
    "profile.section_fleet": {
        "ru": "2. Станочный парк", "uz_latin": "2. Stanoklar parki", "uz_cyrillic": "2. Станоклар парки",
        "en": "2. Machine fleet",
    },
    "profile.save_basic_first": {
        "ru": "(сначала сохраните основную информацию)", "uz_latin": "(avval asosiy maʼlumotni saqlang)",
        "uz_cyrillic": "(аввал асосий маълумотни сақланг)", "en": "(save basic information first)",
    },
    "profile.table_equipment": {
        "ru": "Оборудование", "uz_latin": "Uskuna", "uz_cyrillic": "Ускуна", "en": "Equipment",
    },
    "profile.table_model": {
        "ru": "Модель", "uz_latin": "Model", "uz_cyrillic": "Модель", "en": "Model",
    },
    "profile.table_qty": {
        "ru": "Кол-во", "uz_latin": "Soni", "uz_cyrillic": "Сони", "en": "Qty",
    },
    "profile.table_notes": {
        "ru": "Примечания", "uz_latin": "Izohlar", "uz_cyrillic": "Изоҳлар", "en": "Notes",
    },
    "common.delete": {
        "ru": "Удалить", "uz_latin": "Oʻchirish", "uz_cyrillic": "Ўчириш", "en": "Delete",
    },
    "profile.fleet_empty": {
        "ru": "Станочный парк ещё не заполнен — без него профиль не будет участвовать в подборе заказов.",
        "uz_latin": "Stanoklar parki hali toʻldirilmagan — u boʻlmasa, profil buyurtmalarni tanlashda ishtirok etmaydi.",
        "uz_cyrillic": "Станоклар парки ҳали тўлдирилмаган — у бўлмаса, профиль буюртмаларни танлашда иштирок этмайди.",
        "en": "The machine fleet isn't filled in yet — without it the profile won't participate in order matching.",
    },
    "profile.equipment_type": {
        "ru": "Тип оборудования", "uz_latin": "Uskuna turi", "uz_cyrillic": "Ускуна тури", "en": "Equipment type",
    },
    "profile.model_placeholder": {
        "ru": "Модель", "uz_latin": "Model", "uz_cyrillic": "Модель", "en": "Model",
    },
    "profile.qty_placeholder": {
        "ru": "Кол-во", "uz_latin": "Soni", "uz_cyrillic": "Сони", "en": "Qty",
    },
    "profile.notes_placeholder": {
        "ru": "Примечания", "uz_latin": "Izohlar", "uz_cyrillic": "Изоҳлар", "en": "Notes",
    },
    "profile.add_equipment": {
        "ru": "Добавить оборудование", "uz_latin": "Uskuna qoʻshish", "uz_cyrillic": "Ускуна қўшиш",
        "en": "Add equipment",
    },
    "profile.section_capabilities": {
        "ru": "3. Допустимые габариты, материалы и услуги",
        "uz_latin": "3. Ruxsat etilgan oʻlchamlar, materiallar va xizmatlar",
        "uz_cyrillic": "3. Рухсат этилган ўлчамлар, материаллар ва хизматлар",
        "en": "3. Allowed dimensions, materials and services",
    },
    "profile.max_length": {
        "ru": "Макс. длина, мм", "uz_latin": "Maks. uzunlik, mm", "uz_cyrillic": "Макс. узунлик, мм",
        "en": "Max length, mm",
    },
    "profile.max_diameter": {
        "ru": "Макс. диаметр, мм", "uz_latin": "Maks. diametr, mm", "uz_cyrillic": "Макс. диаметр, мм",
        "en": "Max diameter, mm",
    },
    "profile.max_width": {
        "ru": "Макс. ширина, мм", "uz_latin": "Maks. kenglik, mm", "uz_cyrillic": "Макс. кенглик, мм",
        "en": "Max width, mm",
    },
    "profile.max_height": {
        "ru": "Макс. высота, мм", "uz_latin": "Maks. balandlik, mm", "uz_cyrillic": "Макс. баландлик, мм",
        "en": "Max height, mm",
    },
    "profile.max_weight": {
        "ru": "Макс. вес заготовки, кг", "uz_latin": "Zagotovkaning maks. og‘irligi, kg",
        "uz_cyrillic": "Заготовканинг макс. оғирлиги, кг", "en": "Max workpiece weight, kg",
    },
    "profile.services_legend": {
        "ru": "Категории услуг (по ним идёт подбор заказов)",
        "uz_latin": "Xizmat toifalari (buyurtmalar shular boʻyicha tanlanadi)",
        "uz_cyrillic": "Хизмат тоифалари (буюртмалар шулар бўйича танланади)",
        "en": "Service categories (order matching is based on these)",
    },
    "profile.materials_legend": {
        "ru": "Материалы, с которыми работаете", "uz_latin": "Ishlaydigan materiallaringiz",
        "uz_cyrillic": "Ишлайдиган материалларингиз", "en": "Materials you work with",
    },
    "profile.save_capabilities": {
        "ru": "Сохранить техвозможности", "uz_latin": "Texnik imkoniyatlarni saqlash",
        "uz_cyrillic": "Техник имкониятларни сақлаш", "en": "Save technical capabilities",
    },
    "profile.constructor_title": {
        "ru": "Анкета конструктора", "uz_latin": "Konstruktor anketasi", "uz_cyrillic": "Конструктор анкетаси",
        "en": "Designer profile",
    },
    "profile.constructor_hint": {
        "ru": "Заполните анкету — по ней вас будут находить заказчики и исполнители, у которых нет своего конструктора в штате. Обязательные поля отмечены *.",
        "uz_latin": "Anketani toʻldiring — shtatda konstruktori boʻlmagan buyurtmachilar va ijrochilar sizni shu orqali topadi. Majburiy maydonlar * bilan belgilangan.",
        "uz_cyrillic": "Анкетани тўлдиринг — штатда конструктори бўлмаган буюртмачилар ва ижрочилар сизни шу орқали топади. Мажбурий майдонлар * билан белгиланган.",
        "en": "Fill in the profile — customers and executors without an in-house designer will find you through it. Required fields are marked *.",
    },
    "profile.constructor_complete_badge": {
        "ru": "Анкета заполнена — видна в каталоге", "uz_latin": "Anketa toʻldirilgan — katalogda koʻrinadi",
        "uz_cyrillic": "Анкета тўлдирилган — каталогда кўринади", "en": "Profile complete — visible in the catalog",
    },
    "profile.constructor_incomplete_badge": {
        "ru": "Анкета не заполнена", "uz_latin": "Anketa toʻldirilmagan", "uz_cyrillic": "Анкета тўлдирилмаган",
        "en": "Profile incomplete",
    },
    "profile.studio_name": {
        "ru": "Имя / название студии *", "uz_latin": "Ism / studiya nomi *", "uz_cyrillic": "Исм / студия номи *",
        "en": "Name / studio name *",
    },
    "profile.about_specialization": {
        "ru": "О себе, специализация *", "uz_latin": "O‘zingiz haqingizda, ixtisoslik *",
        "uz_cyrillic": "Ўзингиз ҳақингизда, ихтисослик *", "en": "About you, specialization *",
    },
    "profile.about_placeholder": {
        "ru": "Какие чертежи делаете, в каких программах (КОМПАС, AutoCAD, SolidWorks...), опыт",
        "uz_latin": "Qanday chizmalar tayyorlaysiz, qaysi dasturlarda (KOMPAS, AutoCAD, SolidWorks...), tajriba",
        "uz_cyrillic": "Қандай чизмалар тайёрлайсиз, қайси дастурларда (КОМПАС, AutoCAD, SolidWorks...), тажриба",
        "en": "What drawings you make, which software (KOMPAS, AutoCAD, SolidWorks...), experience",
    },
    "profile.experience_years": {
        "ru": "Опыт работы, лет", "uz_latin": "Ish tajribasi, yil", "uz_cyrillic": "Иш тажрибаси, йил",
        "en": "Years of experience",
    },
    "profile.portfolio_link": {
        "ru": "Ссылка на портфолио", "uz_latin": "Portfolio havolasi", "uz_cyrillic": "Портфолио ҳаволаси",
        "en": "Portfolio link",
    },
    "profile.price_note": {
        "ru": "Стоимость работ", "uz_latin": "Ish narxi", "uz_cyrillic": "Иш нархи", "en": "Pricing",
    },
    "profile.price_note_placeholder": {
        "ru": "Например: от 200 000 сум за чертёж", "uz_latin": "Masalan: chizma uchun 200 000 so‘mdan",
        "uz_cyrillic": "Масалан: чизма учун 200 000 сўмдан", "en": "E.g.: from 200,000 UZS per drawing",
    },
    "profile.map_hint_optional": {
        "ru": "Уточните точку на карте (необязательно — чтобы вас было видно на «Карте»)",
        "uz_latin": "Xaritada nuqtani aniqlashtiring (ixtiyoriy — «Xarita»da koʻrinishingiz uchun)",
        "uz_cyrillic": "Харитада нуқтани аниқлаштиринг (ихтиёрий — «Харита»да кўринишингиз учун)",
        "en": "Refine the point on the map (optional — so you appear on the \"Map\")",
    },
    "profile.save_form": {
        "ru": "Сохранить анкету", "uz_latin": "Anketani saqlash", "uz_cyrillic": "Анкетани сақлаш",
        "en": "Save profile",
    },
    "portfolio.title": {
        "ru": "Портфолио (для рекламы)", "uz_latin": "Portfolio (reklama uchun)", "uz_cyrillic": "Портфолио (реклама учун)",
        "en": "Portfolio (for advertising)",
    },
    "portfolio.hint": {
        "ru": "Фото цеха, станков, продукции или ссылка на видео — то, что увидят на вашей публичной странице.",
        "uz_latin": "Sex, stanoklar, mahsulot fotolari yoki video havolasi — ochiq sahifangizda koʻrinadigan narsalar.",
        "uz_cyrillic": "Сех, станоклар, маҳсулот фотолари ёки видео ҳаволаси — очиқ саҳифангизда кўринадиган нарсалар.",
        "en": "Photos of your shop, machines, products, or a video link — what visitors see on your public page.",
    },
    "portfolio.telegram_before": {
        "ru": "Кстати: чтобы не пропускать уведомления о заказах и откликах, подключите Telegram —",
        "uz_latin": "Aytgancha: buyurtmalar va takliflar haqidagi bildirishnomalarni oʻtkazib yubormaslik uchun Telegramni ulang —",
        "uz_cyrillic": "Айтганча: буюртмалар ва таклифлар ҳақидаги билдиришномаларни ўтказиб юбормаслик учун Telegramни улаnг —",
        "en": "By the way: to not miss notifications about orders and bids, connect Telegram —",
    },
    "portfolio.telegram_click_here": {
        "ru": "нажмите здесь", "uz_latin": "bu yerni bosing", "uz_cyrillic": "бу ерни босинг",
        "en": "click here",
    },
    "portfolio.telegram_mid": {
        "ru": "и в открывшемся боте нажмите", "uz_latin": "va ochilgan botda bosing", "uz_cyrillic": "ва очилган ботда босинг",
        "en": "and in the bot that opens, press",
    },
    "portfolio.telegram_fallback": {
        "ru": "Если вы уже писали этому боту раньше и кнопка не привязала аккаунт — просто отправьте боту сообщением код",
        "uz_latin": "Agar bu botga avval yozgan boʻlsangiz va tugma hisobni bogʻlamagan boʻlsa — botga xabar sifatida shu kodni yuboring",
        "uz_cyrillic": "Агар бу ботга аввал ёзган бўлсангиз ва тугма ҳисобни боғламаган бўлса — ботга хабар сифатида шу кодни юборинг",
        "en": "If you've already messaged this bot before and the button didn't link your account — just send the bot this code as a message:",
    },
    "portfolio.telegram_details": {
        "ru": "подробнее в", "uz_latin": "batafsil:", "uz_cyrillic": "батафсил:", "en": "more details in",
    },
    "portfolio.settings_link_text": {
        "ru": "Настройках", "uz_latin": "Sozlamalarda", "uz_cyrillic": "Созламаларда", "en": "Settings",
    },
    "portfolio.empty": {
        "ru": "Портфолио пока пустое.", "uz_latin": "Portfolio hozircha boʻsh.", "uz_cyrillic": "Портфолио ҳозирча бўш.",
        "en": "Portfolio is empty so far.",
    },
    "portfolio.photo": {
        "ru": "Фото", "uz_latin": "Foto", "uz_cyrillic": "Фото", "en": "Photo",
    },
    "portfolio.caption": {
        "ru": "Подпись", "uz_latin": "Izoh", "uz_cyrillic": "Изоҳ", "en": "Caption",
    },
    "portfolio.caption_placeholder": {
        "ru": "напр. цех токарной обработки", "uz_latin": "masalan, tokarlik sexi", "uz_cyrillic": "масалан, токарлик сехи",
        "en": "e.g. turning workshop",
    },
    "portfolio.add_photo": {
        "ru": "Добавить фото", "uz_latin": "Foto qoʻshish", "uz_cyrillic": "Фото қўшиш", "en": "Add photo",
    },
    "portfolio.video_link": {
        "ru": "Ссылка на видео", "uz_latin": "Video havolasi", "uz_cyrillic": "Видео ҳаволаси", "en": "Video link",
    },
    "portfolio.add_video": {
        "ru": "Добавить видео", "uz_latin": "Video qoʻshish", "uz_cyrillic": "Видео қўшиш", "en": "Add video",
    },
    "portfolio.watch_video": {
        "ru": "▶ Видео", "uz_latin": "▶ Video", "uz_cyrillic": "▶ Видео", "en": "▶ Video",
    },
    "profile.executor_fallback_name": {
        "ru": "Исполнитель", "uz_latin": "Ijrochi", "uz_cyrillic": "Ижрочи", "en": "Executor",
    },
    "profile.org_master_short": {
        "ru": "Мастер", "uz_latin": "Usta", "uz_cyrillic": "Уста", "en": "Craftsman",
    },
    "profile.rating_label": {
        "ru": "рейтинг", "uz_latin": "reyting", "uz_cyrillic": "рейтинг", "en": "rating",
    },
    "profile.workload_display": {
        "ru": "Загруженность: {value}/10", "uz_latin": "Yuklama: {value}/10", "uz_cyrillic": "Юклама: {value}/10",
        "en": "Workload: {value}/10",
    },
    "profile.accepts_payment": {
        "ru": "Принимает оплату:", "uz_latin": "Toʻlov qabul qiladi:", "uz_cyrillic": "Тўлов қабул қилади:",
        "en": "Accepts payment:",
    },
    "common.write_message": {
        "ru": "✉ Написать", "uz_latin": "✉ Yozish", "uz_cyrillic": "✉ Ёзиш", "en": "✉ Message",
    },
    "profile.contacts_label": {
        "ru": "Контакты:", "uz_latin": "Kontaktlar:", "uz_cyrillic": "Контактлар:", "en": "Contacts:",
    },
    "profile.phone_label": {
        "ru": "телефон", "uz_latin": "telefon", "uz_cyrillic": "телефон", "en": "phone",
    },
    "profile.address_label": {
        "ru": "адрес", "uz_latin": "manzil", "uz_cyrillic": "манзил", "en": "address",
    },
    "profile.fleet_title": {
        "ru": "Станочный парк", "uz_latin": "Stanoklar parki", "uz_cyrillic": "Станоклар парки",
        "en": "Machine fleet",
    },
    "profile.pcs_unit": {
        "ru": "шт.", "uz_latin": "dona", "uz_cyrillic": "дона", "en": "pcs",
    },
    "profile.services_title": {
        "ru": "Услуги", "uz_latin": "Xizmatlar", "uz_cyrillic": "Хизматлар", "en": "Services",
    },
    "profile.materials_title": {
        "ru": "Материалы", "uz_latin": "Materiallar", "uz_cyrillic": "Материаллар", "en": "Materials",
    },
    "profile.portfolio_section_title": {
        "ru": "Портфолио", "uz_latin": "Portfolio", "uz_cyrillic": "Портфолио", "en": "Portfolio",
    },
    "profile.customer_fallback_name": {
        "ru": "Заказчик", "uz_latin": "Buyurtmachi", "uz_cyrillic": "Буюртмачи", "en": "Customer",
    },
    "profile.contacts_available": {
        "ru": "Контакты", "uz_latin": "Kontaktlar", "uz_cyrillic": "Контактлар", "en": "Contacts",
    },
    "profile.contacts_available_reason": {
        "ru": "(доступны, так как у вас есть совместная сделка):",
        "uz_latin": "(sizda umumiy bitim borligi uchun ochiq):",
        "uz_cyrillic": "(сизда умумий битим борлиги учун очиқ):",
        "en": "(available because you have a shared deal):",
    },
    "profile.phone_colon": {
        "ru": "Телефон:", "uz_latin": "Telefon:", "uz_cyrillic": "Телефон:", "en": "Phone:",
    },
    "profile.address_colon": {
        "ru": "Адрес:", "uz_latin": "Manzil:", "uz_cyrillic": "Манзил:", "en": "Address:",
    },
    "profile.contacts_hidden": {
        "ru": "Телефон и адрес открываются после того, как вы заключите сделку по заявке этого заказчика.",
        "uz_latin": "Telefon va manzil bu buyurtmachining buyurtmasi boʻyicha bitim tuzganingizdan keyin ochiladi.",
        "uz_cyrillic": "Телефон ва манзил бу буюртмачининг буюртмаси бўйича битим тузганингиздан кейин очилади.",
        "en": "Phone and address are revealed once you make a deal on this customer's order.",
    },
    "order.new_title": {
        "ru": "Новая заявка на изготовление или ремонт", "uz_latin": "Ishlab chiqarish yoki taʼmirlash uchun yangi buyurtma",
        "uz_cyrillic": "Ишлаб чиқариш ёки таъмирлаш учун янги буюртма", "en": "New manufacturing or repair order",
    },
    "order.new_hint": {
        "ru": "Опишите задачу в любом удобном формате — текстом, фото, чертежами, видео. Сразу после публикации мы подберём подходящих исполнителей.",
        "uz_latin": "Vazifani qulay formatda tasvirlang — matn, foto, chizma, video. Eʼlon qilingandan keyin darhol mos ijrochilarni tanlaymiz.",
        "uz_cyrillic": "Вазифани қулай форматда тасвирланг — матн, фото, чизма, видео. Эълон қилингандан кейин дарҳол мос ижрочиларни танлаймиз.",
        "en": "Describe the task in any convenient format — text, photos, drawings, video. Right after publishing we'll match suitable executors.",
    },
    "order.type": {
        "ru": "Тип заявки *", "uz_latin": "Buyurtma turi *", "uz_cyrillic": "Буюртма тури *", "en": "Order type *",
    },
    "order.manufacturing": {
        "ru": "Изготовление", "uz_latin": "Ishlab chiqarish", "uz_cyrillic": "Ишлаб чиқариш",
        "en": "Manufacturing",
    },
    "order.repair": {
        "ru": "Ремонт", "uz_latin": "Taʼmirlash", "uz_cyrillic": "Таъмирлаш", "en": "Repair",
    },
    "order.title_label": {
        "ru": "Название заявки *", "uz_latin": "Buyurtma nomi *", "uz_cyrillic": "Буюртма номи *",
        "en": "Order title *",
    },
    "order.title_placeholder": {
        "ru": "напр. Токарная обточка вала, 5 шт.", "uz_latin": "masalan, Valni tokarlik bilan ishlash, 5 dona",
        "uz_cyrillic": "масалан, Вални токарлик билан ишлаш, 5 дона", "en": "e.g. Turning a shaft, 5 pcs.",
    },
    "order.description_label": {
        "ru": "Описание *", "uz_latin": "Tavsif *", "uz_cyrillic": "Тавсиф *", "en": "Description *",
    },
    "order.description_placeholder": {
        "ru": "Что нужно сделать, какие требования, есть ли чертёж",
        "uz_latin": "Nima qilish kerak, qanday talablar, chizma bormi",
        "uz_cyrillic": "Нима қилиш керак, қандай талаблар, чизма борми",
        "en": "What needs to be done, requirements, is there a drawing",
    },
    "order.service_category": {
        "ru": "Категория работ *", "uz_latin": "Ish toifasi *", "uz_cyrillic": "Иш тоифаси *",
        "en": "Work category *",
    },
    "order.material": {
        "ru": "Материал", "uz_latin": "Material", "uz_cyrillic": "Материал", "en": "Material",
    },
    "order.material_any": {
        "ru": "— не важно / не знаю —", "uz_latin": "— muhim emas / bilmayman —",
        "uz_cyrillic": "— муҳим эмас / билмайман —", "en": "— doesn't matter / don't know —",
    },
    "order.dimensions_title": {
        "ru": "Параметры детали (необязательно, но повышают точность подбора)",
        "uz_latin": "Detal parametrlari (ixtiyoriy, lekin tanlash aniqligini oshiradi)",
        "uz_cyrillic": "Детал параметрлари (ихтиёрий, лекин танлаш аниқлигини оширади)",
        "en": "Part parameters (optional, but improves matching accuracy)",
    },
    "order.length_mm": {
        "ru": "Длина, мм", "uz_latin": "Uzunlik, mm", "uz_cyrillic": "Узунлик, мм", "en": "Length, mm",
    },
    "order.diameter_mm": {
        "ru": "Диаметр, мм", "uz_latin": "Diametr, mm", "uz_cyrillic": "Диаметр, мм", "en": "Diameter, mm",
    },
    "order.width_mm": {
        "ru": "Ширина, мм", "uz_latin": "Kenglik, mm", "uz_cyrillic": "Кенглик, мм", "en": "Width, mm",
    },
    "order.height_mm": {
        "ru": "Высота, мм", "uz_latin": "Balandlik, mm", "uz_cyrillic": "Баландлик, мм", "en": "Height, mm",
    },
    "order.weight_kg": {
        "ru": "Вес заготовки, кг", "uz_latin": "Zagotovka og‘irligi, kg", "uz_cyrillic": "Заготовка оғирлиги, кг",
        "en": "Workpiece weight, kg",
    },
    "order.media_title": {
        "ru": "Медиа", "uz_latin": "Media", "uz_cyrillic": "Медиа", "en": "Media",
    },
    "order.photos_label": {
        "ru": "Фото (можно несколько)", "uz_latin": "Foto (bir nechta boʻlishi mumkin)",
        "uz_cyrillic": "Фото (бир нечта бўлиши мумкин)", "en": "Photos (multiple allowed)",
    },
    "order.drawing_label": {
        "ru": "Чертёж (изображение)", "uz_latin": "Chizma (rasm)", "uz_cyrillic": "Чизма (расм)",
        "en": "Drawing (image)",
    },
    "order.video_url_label": {
        "ru": "Ссылка на видео (YouTube, Google Диск и т.п.)",
        "uz_latin": "Video havolasi (YouTube, Google Disk va h.k.)",
        "uz_cyrillic": "Видео ҳаволаси (YouTube, Google Disk ва ҳ.к.)",
        "en": "Video link (YouTube, Google Drive, etc.)",
    },
    "order.document_url_label": {
        "ru": "Ссылка на документ (PDF-чертёж и т.п.)",
        "uz_latin": "Hujjat havolasi (PDF-chizma va h.k.)",
        "uz_cyrillic": "Ҳужжат ҳаволаси (PDF-чизма ва ҳ.к.)",
        "en": "Document link (PDF drawing, etc.)",
    },
    "order.location_title": {
        "ru": "Локация и условия", "uz_latin": "Joylashuv va shartlar", "uz_cyrillic": "Жойлашув ва шартлар",
        "en": "Location and terms",
    },
    "order.site_address": {
        "ru": "Адрес объекта", "uz_latin": "Obyekt manzili", "uz_cyrillic": "Объект манзили", "en": "Site address",
    },
    "order.site_address_placeholder": {
        "ru": "для ремонта на месте", "uz_latin": "joyida taʼmirlash uchun", "uz_cyrillic": "жойида таъмирлаш учун",
        "en": "for on-site repair",
    },
    "order.map_hint": {
        "ru": "Уточните точку на карте", "uz_latin": "Xaritada nuqtani aniqlashtiring",
        "uz_cyrillic": "Харитада нуқтани аниқлаштиринг", "en": "Refine the point on the map",
    },
    "order.payment_methods_legend": {
        "ru": "Способ оплаты (необязательно)", "uz_latin": "Toʻlov usuli (ixtiyoriy)",
        "uz_cyrillic": "Тўлов усули (ихтиёрий)", "en": "Payment method (optional)",
    },
    "order.budget_min": {
        "ru": "Бюджет от, UZS", "uz_latin": "Byudjet dan, UZS", "uz_cyrillic": "Бюджет дан, UZS",
        "en": "Budget from, UZS",
    },
    "order.budget_max": {
        "ru": "Бюджет до, UZS", "uz_latin": "Byudjet gacha, UZS", "uz_cyrillic": "Бюджет гача, UZS",
        "en": "Budget to, UZS",
    },
    "order.deadline_date": {
        "ru": "Желаемый срок", "uz_latin": "Xohlagan muddat", "uz_cyrillic": "Хоҳлаган муддат",
        "en": "Desired deadline",
    },
    "order.auction_duration": {
        "ru": "Длительность аукциона", "uz_latin": "Auksion davomiyligi", "uz_cyrillic": "Аукцион давомийлиги",
        "en": "Auction duration",
    },
    "order.24h": {
        "ru": "24 часа", "uz_latin": "24 soat", "uz_cyrillic": "24 соат", "en": "24 hours",
    },
    "order.48h": {
        "ru": "48 часов", "uz_latin": "48 soat", "uz_cyrillic": "48 соат", "en": "48 hours",
    },
    "order.72h": {
        "ru": "72 часа", "uz_latin": "72 soat", "uz_cyrillic": "72 соат", "en": "72 hours",
    },
    "order.publish": {
        "ru": "Опубликовать заявку", "uz_latin": "Buyurtmani eʼlon qilish", "uz_cyrillic": "Буюртмани эълон қилиш",
        "en": "Publish order",
    },
    "order.status_published": {
        "ru": "опубликован", "uz_latin": "eʼlon qilingan", "uz_cyrillic": "эълон қилинган", "en": "published",
    },
    "order.status_assigned": {
        "ru": "исполнитель выбран", "uz_latin": "ijrochi tanlandi", "uz_cyrillic": "ижрочи танланди",
        "en": "executor selected",
    },
    "order.status_in_progress": {
        "ru": "в работе", "uz_latin": "bajarilmoqda", "uz_cyrillic": "бажарилмоқда", "en": "in progress",
    },
    "order.status_completed": {
        "ru": "завершён", "uz_latin": "yakunlandi", "uz_cyrillic": "якунланди", "en": "completed",
    },
    "order.status_disputed": {
        "ru": "спор", "uz_latin": "nizo", "uz_cyrillic": "низо", "en": "disputed",
    },
    "order.my_orders_title": {
        "ru": "Мои заказы", "uz_latin": "Mening buyurtmalarim", "uz_cyrillic": "Менинг буюртмаларим",
        "en": "My orders",
    },
    "order.table_number": {
        "ru": "№", "uz_latin": "№", "uz_cyrillic": "№", "en": "No.",
    },
    "order.table_order": {
        "ru": "Заявка", "uz_latin": "Buyurtma", "uz_cyrillic": "Буюртма", "en": "Order",
    },
    "order.table_category": {
        "ru": "Категория", "uz_latin": "Toifa", "uz_cyrillic": "Тоифа", "en": "Category",
    },
    "order.table_status": {
        "ru": "Статус", "uz_latin": "Holat", "uz_cyrillic": "Ҳолат", "en": "Status",
    },
    "order.table_bids": {
        "ru": "Ставок", "uz_latin": "Takliflar", "uz_cyrillic": "Таклифлар", "en": "Bids",
    },
    "order.table_created": {
        "ru": "Создан", "uz_latin": "Yaratilgan", "uz_cyrillic": "Яратилган", "en": "Created",
    },
    "common.open": {
        "ru": "Открыть", "uz_latin": "Ochish", "uz_cyrillic": "Очиш", "en": "Open",
    },
    "order.no_orders_yet": {
        "ru": "Заявок пока нет.", "uz_latin": "Hozircha buyurtmalar yoʻq.", "uz_cyrillic": "Ҳозирча буюртмалар йўқ.",
        "en": "No orders yet.",
    },
    "order.post_first": {
        "ru": "Разместить первую", "uz_latin": "Birinchisini joylashtirish", "uz_cyrillic": "Биринчисини жойлаштириш",
        "en": "Post the first one",
    },
    "order.status_cancelled": {
        "ru": "отменён", "uz_latin": "bekor qilindi", "uz_cyrillic": "бекор қилинди", "en": "cancelled",
    },
    "bid.status_active": {
        "ru": "активна", "uz_latin": "faol", "uz_cyrillic": "фаол", "en": "active",
    },
    "bid.status_accepted": {
        "ru": "принята", "uz_latin": "qabul qilindi", "uz_cyrillic": "қабул қилинди", "en": "accepted",
    },
    "bid.status_rejected": {
        "ru": "отклонена", "uz_latin": "rad etildi", "uz_cyrillic": "рад этилди", "en": "rejected",
    },
    "bid.status_withdrawn": {
        "ru": "отозвана", "uz_latin": "qaytarib olindi", "uz_cyrillic": "қайтариб олинди", "en": "withdrawn",
    },
    "order.dashboard_title": {
        "ru": "Лента заказов", "uz_latin": "Buyurtmalar lentasi", "uz_cyrillic": "Буюртмалар ленталари",
        "en": "Orders feed",
    },
    "order.dashboard_hint": {
        "ru": "Все открытые заявки. Отмеченные «Рекомендуем» лучше всего подходят под ваш профиль (станочный парк, габариты, регион).",
        "uz_latin": "Barcha ochiq buyurtmalar. «Tavsiya etamiz» belgisi profilingizga (stanoklar parki, oʻlchamlar, viloyat) eng mos kelganini bildiradi.",
        "uz_cyrillic": "Барча очиқ буюртмалар. «Тавсия этамиз» белгиси профилингизга (станоклар парки, ўлчамлар, вилоят) энг мос келганини билдиради.",
        "en": "All open orders. Those marked \"Recommended\" best match your profile (machine fleet, dimensions, region).",
    },
    "order.recommended_badge": {
        "ru": "Рекомендуем", "uz_latin": "Tavsiya etamiz", "uz_cyrillic": "Тавсия этамиз", "en": "Recommended",
    },
    "order.table_distance": {
        "ru": "Расстояние", "uz_latin": "Masofa", "uz_cyrillic": "Масофа", "en": "Distance",
    },
    "order.table_my_bid": {
        "ru": "Моя ставка", "uz_latin": "Mening taklifim", "uz_cyrillic": "Менинг таклифим", "en": "My bid",
    },
    "order.km_short": {
        "ru": "{value} км", "uz_latin": "{value} km", "uz_cyrillic": "{value} км", "en": "{value} km",
    },
    "order.days_short": {
        "ru": "дн.", "uz_latin": "kun", "uz_cyrillic": "кун", "en": "days",
    },
    "order.no_open_orders": {
        "ru": "Пока нет открытых заявок — как только заказчик опубликует новую, вы увидите её здесь.",
        "uz_latin": "Hozircha ochiq buyurtmalar yoʻq — buyurtmachi yangisini eʼlon qilishi bilan uni shu yerda koʻrasiz.",
        "uz_cyrillic": "Ҳозирча очиқ буюртмалар йўқ — буюртмачи янгисини эълон қилиши билан уни шу ерда кўрасиз.",
        "en": "No open orders yet — as soon as a customer posts a new one, you'll see it here.",
    },
    "order.number_title": {
        "ru": "Заявка №{id}: {title}", "uz_latin": "Buyurtma №{id}: {title}", "uz_cyrillic": "Буюртма №{id}: {title}",
        "en": "Order #{id}: {title}",
    },
    "order.material_label": {
        "ru": "Материал:", "uz_latin": "Material:", "uz_cyrillic": "Материал:", "en": "Material:",
    },
    "order.deadline_label": {
        "ru": "Срок: до {date}", "uz_latin": "Muddat: {date} gacha", "uz_cyrillic": "Муддат: {date} гача",
        "en": "Deadline: by {date}",
    },
    "order.budget_label": {
        "ru": "Бюджет: {min}–{max} UZS", "uz_latin": "Byudjet: {min}–{max} UZS", "uz_cyrillic": "Бюджет: {min}–{max} UZS",
        "en": "Budget: {min}–{max} UZS",
    },
    "order.payment_label": {
        "ru": "Оплата: {methods}", "uz_latin": "Toʻlov: {methods}", "uz_cyrillic": "Тўлов: {methods}",
        "en": "Payment: {methods}",
    },
    "order.customer_profile_link": {
        "ru": "Профиль и портфолио заказчика ↗", "uz_latin": "Buyurtmachi profili va portfolio ↗",
        "uz_cyrillic": "Буюртмачи профили ва портфолио ↗", "en": "Customer profile and portfolio ↗",
    },
    "order.write_chat": {
        "ru": "Написать 💬", "uz_latin": "Yozish 💬", "uz_cyrillic": "Ёзиш 💬", "en": "Message 💬",
    },
    "review.leave": {
        "ru": "Оставить отзыв", "uz_latin": "Sharh qoldirish", "uz_cyrillic": "Шарҳ қолдириш",
        "en": "Leave a review",
    },
    "dispute.for_order": {
        "ru": "Спор по заказу ({status})", "uz_latin": "Buyurtma boʻyicha nizo ({status})",
        "uz_cyrillic": "Буюртма бўйича низо ({status})", "en": "Order dispute ({status})",
    },
    "dispute.open": {
        "ru": "Открыть спор", "uz_latin": "Nizo ochish", "uz_cyrillic": "Низо очиш", "en": "Open dispute",
    },
    "order.dimensions_label": {
        "ru": "Габариты:", "uz_latin": "Oʻlchamlar:", "uz_cyrillic": "Ўлчамлар:", "en": "Dimensions:",
    },
    "order.length_short": {
        "ru": "длина {value} мм", "uz_latin": "uzunlik {value} mm", "uz_cyrillic": "узунлик {value} мм",
        "en": "length {value} mm",
    },
    "order.diameter_short": {
        "ru": ", диаметр {value} мм", "uz_latin": ", diametr {value} mm", "uz_cyrillic": ", диаметр {value} мм",
        "en": ", diameter {value} mm",
    },
    "order.weight_short": {
        "ru": ", вес {value} кг", "uz_latin": ", og‘irligi {value} kg", "uz_cyrillic": ", оғирлиги {value} кг",
        "en": ", weight {value} kg",
    },
    "order.video_link_text": {
        "ru": "Видео ↗", "uz_latin": "Video ↗", "uz_cyrillic": "Видео ↗", "en": "Video ↗",
    },
    "order.document_link_text": {
        "ru": "Документ ↗", "uz_latin": "Hujjat ↗", "uz_cyrillic": "Ҳужжат ↗", "en": "Document ↗",
    },
    "order.executor_section": {
        "ru": "Исполнитель", "uz_latin": "Ijrochi", "uz_cyrillic": "Ижрочи", "en": "Executor",
    },
    "order.deadline_until": {
        "ru": "срок до {date}", "uz_latin": "muddat {date} gacha", "uz_cyrillic": "муддат {date} гача",
        "en": "deadline by {date}",
    },
    "order.confirm_completion": {
        "ru": "Подтвердить приёмку заказа", "uz_latin": "Buyurtma qabulini tasdiqlash",
        "uz_cyrillic": "Буюртма қабулини тасдиқлаш", "en": "Confirm order acceptance",
    },
    "order.cancel_selection_confirm": {
        "ru": "Отменить выбор исполнителя? Заявка снова откроется для ставок.",
        "uz_latin": "Ijrochi tanlovini bekor qilasizmi? Buyurtma yana takliflar uchun ochiladi.",
        "uz_cyrillic": "Ижрочи танловини бекор қиласизми? Буюртма яна таклифлар учун очилади.",
        "en": "Cancel the executor selection? The order will reopen for bids.",
    },
    "order.cancel_selection": {
        "ru": "Отменить выбор", "uz_latin": "Tanlovni bekor qilish", "uz_cyrillic": "Танловни бекор қилиш",
        "en": "Cancel selection",
    },
    "order.bids_section": {
        "ru": "Ставки исполнителей ({count})", "uz_latin": "Ijrochilar takliflari ({count})",
        "uz_cyrillic": "Ижрочилар таклифлари ({count})", "en": "Executor bids ({count})",
    },
    "order.table_executor": {
        "ru": "Исполнитель", "uz_latin": "Ijrochi", "uz_cyrillic": "Ижрочи", "en": "Executor",
    },
    "order.table_price": {
        "ru": "Цена", "uz_latin": "Narx", "uz_cyrillic": "Нарх", "en": "Price",
    },
    "order.table_deadline": {
        "ru": "Срок", "uz_latin": "Muddat", "uz_cyrillic": "Муддат", "en": "Deadline",
    },
    "order.table_comment": {
        "ru": "Комментарий", "uz_latin": "Izoh", "uz_cyrillic": "Изоҳ", "en": "Comment",
    },
    "order.no_rating": {
        "ru": "нет рейтинга", "uz_latin": "reyting yoʻq", "uz_cyrillic": "рейтинг йўқ", "en": "no rating",
    },
    "order.select_bid": {
        "ru": "Выбрать", "uz_latin": "Tanlash", "uz_cyrillic": "Танлаш", "en": "Select",
    },
    "order.no_bids_yet": {
        "ru": "Ставок пока нет", "uz_latin": "Hozircha takliflar yoʻq", "uz_cyrillic": "Ҳозирча таклифлар йўқ",
        "en": "No bids yet",
    },
    "order.auction_open_until": {
        "ru": " — аукцион открыт до {date}", "uz_latin": " — auksion {date} gacha ochiq",
        "uz_cyrillic": " — аукцион {date} гача очиқ", "en": " — auction open until {date}",
    },
    "order.your_order_section": {
        "ru": "Ваш заказ", "uz_latin": "Sizning buyurtmangiz", "uz_cyrillic": "Сизнинг буюртмангиз",
        "en": "Your order",
    },
    "order.agreed_price_label": {
        "ru": "Согласованная цена: {price} {currency}", "uz_latin": "Kelishilgan narx: {price} {currency}",
        "uz_cyrillic": "Келишилган нарх: {price} {currency}", "en": "Agreed price: {price} {currency}",
    },
    "order.start_work": {
        "ru": "Начать работу", "uz_latin": "Ishni boshlash", "uz_cyrillic": "Ишни бошлаш", "en": "Start work",
    },
    "order.your_bid_section": {
        "ru": "Ваша ставка", "uz_latin": "Sizning taklifingiz", "uz_cyrillic": "Сизнинг таклифингиз",
        "en": "Your bid",
    },
    "order.submit_bid_section": {
        "ru": "Подать ставку", "uz_latin": "Taklif berish", "uz_cyrillic": "Таклиф бериш", "en": "Submit a bid",
    },
    "order.price_field": {
        "ru": "Цена", "uz_latin": "Narx", "uz_cyrillic": "Нарх", "en": "Price",
    },
    "order.currency_field": {
        "ru": "Валюта", "uz_latin": "Valyuta", "uz_cyrillic": "Валюта", "en": "Currency",
    },
    "order.lead_time_field": {
        "ru": "Срок выполнения, дней", "uz_latin": "Bajarish muddati, kun", "uz_cyrillic": "Бажариш муддати, кун",
        "en": "Completion time, days",
    },
    "order.comment_field": {
        "ru": "Комментарий (условия, гарантия)", "uz_latin": "Izoh (shartlar, kafolat)",
        "uz_cyrillic": "Изоҳ (шартлар, кафолат)", "en": "Comment (terms, warranty)",
    },
    "order.update_bid": {
        "ru": "Обновить ставку", "uz_latin": "Taklifni yangilash", "uz_cyrillic": "Таклифни янгилаш",
        "en": "Update bid",
    },
    "order.submit_bid_btn": {
        "ru": "Отправить ставку", "uz_latin": "Taklifni yuborish", "uz_cyrillic": "Таклифни юбориш",
        "en": "Submit bid",
    },
    "order.complete_profile_before": {
        "ru": "Чтобы делать ставки, сначала", "uz_latin": "Taklif berish uchun avval",
        "uz_cyrillic": "Таклиф бериш учун аввал", "en": "To place bids, first",
    },
    "order.complete_profile_link": {
        "ru": "полностью заполните профиль", "uz_latin": "profilni toʻliq toʻldiring",
        "uz_cyrillic": "профилни тўлиқ тўлдиринг", "en": "complete your profile fully",
    },
    "order.your_bid_closed": {
        "ru": "Ваша ставка: {price} {currency} ({status}). Аукцион закрыт.",
        "uz_latin": "Sizning taklifingiz: {price} {currency} ({status}). Auksion yopiq.",
        "uz_cyrillic": "Сизнинг таклифингиз: {price} {currency} ({status}). Аукцион ёпиқ.",
        "en": "Your bid: {price} {currency} ({status}). The auction is closed.",
    },
    "listing.sell": {
        "ru": "Продаю", "uz_latin": "Sotaman", "uz_cyrillic": "Сотаман", "en": "Selling",
    },
    "listing.buy": {
        "ru": "Куплю", "uz_latin": "Sotib olaman", "uz_cyrillic": "Сотиб оламан", "en": "Buying",
    },
    "listing.looking_to_buy": {
        "ru": "Ищу купить", "uz_latin": "Sotib olmoqchiman", "uz_cyrillic": "Сотиб олмоқчиман", "en": "Looking to buy",
    },
    "listing.price_not_set": {
        "ru": "Цена не указана", "uz_latin": "Narx koʻrsatilmagan", "uz_cyrillic": "Нарх кўрсатилмаган",
        "en": "Price not specified",
    },
    "listing.negotiable": {
        "ru": "торг", "uz_latin": "kelishiladi", "uz_cyrillic": "келишилади", "en": "negotiable",
    },
    "listing.negotiable_checkbox": {
        "ru": "Торг уместен", "uz_latin": "Kelishish mumkin", "uz_cyrillic": "Келишиш мумкин",
        "en": "Price negotiable",
    },
    "listing.no_listings": {
        "ru": "Пока нет объявлений по этим фильтрам.", "uz_latin": "Bu filtrlar boʻyicha eʼlonlar hozircha yoʻq.",
        "uz_cyrillic": "Бу фильтрлар бўйича эълонлар ҳозирча йўқ.", "en": "No listings match these filters yet.",
    },
    "listing.post_listing": {
        "ru": "Разместить объявление", "uz_latin": "Eʼlon joylashtirish", "uz_cyrillic": "Эълон жойлаштириш",
        "en": "Post a listing",
    },
    "listing.filter_type": {
        "ru": "Тип", "uz_latin": "Turi", "uz_cyrillic": "Тури", "en": "Type",
    },
    "listing.filter_all": {
        "ru": "Все", "uz_latin": "Barchasi", "uz_cyrillic": "Барчаси", "en": "All",
    },
    "listing.filter_region": {
        "ru": "Регион", "uz_latin": "Viloyat", "uz_cyrillic": "Вилоят", "en": "Region",
    },
    "listing.filter_category": {
        "ru": "Категория", "uz_latin": "Toifa", "uz_cyrillic": "Тоифа", "en": "Category",
    },
    "listing.marketplace_title": {
        "ru": "Барахолка: станки и инструмент", "uz_latin": "Bozorcha: stanoklar va asboblar",
        "uz_cyrillic": "Бозорча: станоклар ва асбоблар", "en": "Marketplace: machines and tools",
    },
    "listing.type_label": {
        "ru": "Тип объявления *", "uz_latin": "Eʼlon turi *", "uz_cyrillic": "Эълон тури *",
        "en": "Listing type *",
    },
    "listing.category_label": {
        "ru": "Категория *", "uz_latin": "Toifa *", "uz_cyrillic": "Тоифа *", "en": "Category *",
    },
    "listing.title_label": {
        "ru": "Название *", "uz_latin": "Nomi *", "uz_cyrillic": "Номи *", "en": "Title *",
    },
    "listing.title_placeholder_marketplace": {
        "ru": "напр. Токарный станок 1К62, б/у", "uz_latin": "masalan, Tokarlik stanogi 1K62, ishlatilgan",
        "uz_cyrillic": "масалан, Токарлик станоги 1К62, ишлатилган", "en": "e.g. Lathe 1K62, used",
    },
    "listing.description_label": {
        "ru": "Описание *", "uz_latin": "Tavsif *", "uz_cyrillic": "Тавсиф *", "en": "Description *",
    },
    "listing.condition_legend": {
        "ru": "Состояние (для «Продаю»)", "uz_latin": "Holati («Sotaman» uchun)",
        "uz_cyrillic": "Ҳолати («Сотаман» учун)", "en": "Condition (for \"Selling\")",
    },
    "listing.condition_new": {
        "ru": "Новое", "uz_latin": "Yangi", "uz_cyrillic": "Янги", "en": "New",
    },
    "listing.condition_used": {
        "ru": "Б/у", "uz_latin": "Ishlatilgan", "uz_cyrillic": "Ишлатилган", "en": "Used",
    },
    "listing.condition_parts": {
        "ru": "На запчасти", "uz_latin": "Ehtiyot qismlarga", "uz_cyrillic": "Эҳтиёт қисмларга",
        "en": "For parts",
    },
    "listing.price_label": {
        "ru": "Цена", "uz_latin": "Narx", "uz_cyrillic": "Нарх", "en": "Price",
    },
    "listing.currency_label": {
        "ru": "Валюта", "uz_latin": "Valyuta", "uz_cyrillic": "Валюта", "en": "Currency",
    },
    "listing.region_required": {
        "ru": "Регион *", "uz_latin": "Viloyat *", "uz_cyrillic": "Вилоят *", "en": "Region *",
    },
    "listing.payment_methods_legend": {
        "ru": "Способ оплаты (необязательно)", "uz_latin": "Toʻlov usuli (ixtiyoriy)",
        "uz_cyrillic": "Тўлов усули (ихтиёрий)", "en": "Payment method (optional)",
    },
    "listing.delivery_legend": {
        "ru": "Доставка (необязательно)", "uz_latin": "Yetkazib berish (ixtiyoriy)",
        "uz_cyrillic": "Етказиб бериш (ихтиёрий)", "en": "Delivery (optional)",
    },
    "listing.photos_label": {
        "ru": "Фото (можно несколько)", "uz_latin": "Foto (bir nechta boʻlishi mumkin)",
        "uz_cyrillic": "Фото (бир нечта бўлиши мумкин)", "en": "Photos (multiple allowed)",
    },
    "listing.map_hint": {
        "ru": "Отметьте на карте, где вас найти (необязательно — чтобы объявление было видно на «Карте»)",
        "uz_latin": "Sizni qayerdan topish mumkinligini xaritada belgilang (ixtiyoriy — eʼlon «Xarita»da koʻrinishi uchun)",
        "uz_cyrillic": "Сизни қаердан топиш мумкинлигини харитада белгиланг (ихтиёрий — эълон «Харита»да кўриниши учун)",
        "en": "Mark on the map where to find you (optional — so the listing appears on the \"Map\")",
    },
    "listing.publish": {
        "ru": "Опубликовать", "uz_latin": "Eʼlon qilish", "uz_cyrillic": "Эълон қилиш", "en": "Publish",
    },
    "listing.write_to_author": {
        "ru": "✉ Написать автору", "uz_latin": "✉ Muallifga yozish", "uz_cyrillic": "✉ Муаллифга ёзиш",
        "en": "✉ Message the author",
    },
    "listing.condition_state": {
        "ru": "Состояние: {value}", "uz_latin": "Holati: {value}", "uz_cyrillic": "Ҳолати: {value}",
        "en": "Condition: {value}",
    },
    "listing.delivery_state": {
        "ru": "Доставка: {value}", "uz_latin": "Yetkazib berish: {value}", "uz_cyrillic": "Етказиб бериш: {value}",
        "en": "Delivery: {value}",
    },
    "listing.payment_state": {
        "ru": "Оплата: {value}", "uz_latin": "Toʻlov: {value}", "uz_cyrillic": "Тўлов: {value}",
        "en": "Payment: {value}",
    },
    "listing.photo_alt": {
        "ru": "фото", "uz_latin": "foto", "uz_cyrillic": "фото", "en": "photo",
    },
    "listing.responses_section": {
        "ru": "Отклики ({count})", "uz_latin": "Takliflar ({count})", "uz_cyrillic": "Таклифлар ({count})",
        "en": "Responses ({count})",
    },
    "listing.offered_price": {
        "ru": " — предложено {value}", "uz_latin": " — taklif qilingan {value}", "uz_cyrillic": " — таклиф қилинган {value}",
        "en": " — offered {value}",
    },
    "listing.no_responses": {
        "ru": "Откликов пока нет.", "uz_latin": "Hozircha takliflar yoʻq.", "uz_cyrillic": "Ҳозирча таклифлар йўқ.",
        "en": "No responses yet.",
    },
    "listing.status_label": {
        "ru": "Статус", "uz_latin": "Holat", "uz_cyrillic": "Ҳолат", "en": "Status",
    },
    "listing.status_active": {
        "ru": "Активно", "uz_latin": "Faol", "uz_cyrillic": "Фаол", "en": "Active",
    },
    "listing.status_reserved": {
        "ru": "Зарезервировано", "uz_latin": "Zaxiralangan", "uz_cyrillic": "Захираланган", "en": "Reserved",
    },
    "listing.status_closed": {
        "ru": "Сделка состоялась", "uz_latin": "Bitim tuzildi", "uz_cyrillic": "Битим тузилди",
        "en": "Deal closed",
    },
    "common.update": {
        "ru": "Обновить", "uz_latin": "Yangilash", "uz_cyrillic": "Янгилаш", "en": "Update",
    },
    "listing.respond_section": {
        "ru": "Откликнуться", "uz_latin": "Taklif berish", "uz_cyrillic": "Таклиф бериш", "en": "Respond",
    },
    "listing.message_label": {
        "ru": "Сообщение", "uz_latin": "Xabar", "uz_cyrillic": "Хабар", "en": "Message",
    },
    "listing.message_placeholder": {
        "ru": "Интересует, уточните...", "uz_latin": "Qiziqaman, aniqlashtiring...", "uz_cyrillic": "Қизиқаман, аниқлаштиринг...",
        "en": "Interested, please clarify...",
    },
    "listing.offered_price_label": {
        "ru": "Ваша цена (если торг)", "uz_latin": "Sizning narxingiz (agar kelishiladigan boʻlsa)",
        "uz_cyrillic": "Сизнинг нархингиз (агар келишиладиган бўлса)", "en": "Your price (if negotiable)",
    },
    "listing.send_response": {
        "ru": "Отправить отклик", "uz_latin": "Taklifni yuborish", "uz_cyrillic": "Таклифни юбориш",
        "en": "Send response",
    },
    "listing.not_active": {
        "ru": "Объявление больше не активно.", "uz_latin": "Eʼlon endi faol emas.", "uz_cyrillic": "Эълон энди фаол эмас.",
        "en": "This listing is no longer active.",
    },
    "material.market_title": {
        "ru": "Материалы и сырьё", "uz_latin": "Materiallar va xomashyo", "uz_cyrillic": "Материаллар ва хомашё",
        "en": "Materials and raw stock",
    },
    "material.filter_material": {
        "ru": "Материал", "uz_latin": "Material", "uz_cyrillic": "Материал", "en": "Material",
    },
    "material.filter_form": {
        "ru": "Вид/форма", "uz_latin": "Turi/shakli", "uz_cyrillic": "Тури/шакли", "en": "Kind/form",
    },
    "material.new_title": {
        "ru": "Новое объявление о материале", "uz_latin": "Material haqida yangi eʼlon",
        "uz_cyrillic": "Материал ҳақида янги эълон", "en": "New material listing",
    },
    "material.new_heading": {
        "ru": "Новое объявление: материал/сырьё", "uz_latin": "Yangi eʼlon: material/xomashyo",
        "uz_cyrillic": "Янги эълон: материал/хомашё", "en": "New listing: material/raw stock",
    },
    "material.material_required": {
        "ru": "Материал *", "uz_latin": "Material *", "uz_cyrillic": "Материал *", "en": "Material *",
    },
    "material.form_field": {
        "ru": "Вид/форма", "uz_latin": "Turi/shakli", "uz_cyrillic": "Тури/шакли", "en": "Kind/form",
    },
    "material.form_any": {
        "ru": "— не важно —", "uz_latin": "— muhim emas —", "uz_cyrillic": "— муҳим эмас —", "en": "— any —",
    },
    "material.title_placeholder": {
        "ru": "напр. Лист нержавейки AISI 304, 2 мм", "uz_latin": "masalan, AISI 304 zanglamas list, 2 mm",
        "uz_cyrillic": "масалан, AISI 304 зангламас лист, 2 мм", "en": "e.g. AISI 304 stainless sheet, 2 mm",
    },
    "material.quantity_label": {
        "ru": "Количество", "uz_latin": "Miqdori", "uz_cyrillic": "Миқдори", "en": "Quantity",
    },
    "material.unit_label": {
        "ru": "Единица", "uz_latin": "Birlik", "uz_cyrillic": "Бирлик", "en": "Unit",
    },
    "material.unit_kg": {
        "ru": "кг", "uz_latin": "kg", "uz_cyrillic": "кг", "en": "kg",
    },
    "material.unit_t": {
        "ru": "тонны", "uz_latin": "tonna", "uz_cyrillic": "тонна", "en": "tons",
    },
    "material.unit_m": {
        "ru": "метры", "uz_latin": "metr", "uz_cyrillic": "метр", "en": "meters",
    },
    "material.unit_m2": {
        "ru": "м²", "uz_latin": "m²", "uz_cyrillic": "м²", "en": "m²",
    },
    "material.unit_pcs": {
        "ru": "шт", "uz_latin": "dona", "uz_cyrillic": "дона", "en": "pcs",
    },
    "job.vacancies_title": {
        "ru": "Вакансии", "uz_latin": "Ish oʻrinlari", "uz_cyrillic": "Иш ўринлари", "en": "Jobs",
    },
    "job.post_vacancy": {
        "ru": "Разместить вакансию", "uz_latin": "Ish oʻrni joylashtirish", "uz_cyrillic": "Иш ўрни жойлаштириш",
        "en": "Post a job",
    },
    "job.filter_profession": {
        "ru": "Профессия", "uz_latin": "Kasb", "uz_cyrillic": "Касб", "en": "Profession",
    },
    "job.table_vacancy": {
        "ru": "Вакансия", "uz_latin": "Ish oʻrni", "uz_cyrillic": "Иш ўрни", "en": "Job",
    },
    "job.table_profession": {
        "ru": "Профессия", "uz_latin": "Kasb", "uz_cyrillic": "Касб", "en": "Profession",
    },
    "job.table_salary": {
        "ru": "Зарплата", "uz_latin": "Ish haqi", "uz_cyrillic": "Иш ҳақи", "en": "Salary",
    },
    "job.no_vacancies": {
        "ru": "Пока нет вакансий по этим фильтрам.", "uz_latin": "Bu filtrlar boʻyicha ish oʻrinlari hozircha yoʻq.",
        "uz_cyrillic": "Бу фильтрлар бўйича иш ўринлари ҳозирча йўқ.", "en": "No jobs match these filters yet.",
    },
    "job.new_vacancy_title": {
        "ru": "Новая вакансия", "uz_latin": "Yangi ish oʻrni", "uz_cyrillic": "Янги иш ўрни", "en": "New job",
    },
    "job.title_field": {
        "ru": "Название *", "uz_latin": "Nomi *", "uz_cyrillic": "Номи *", "en": "Title *",
    },
    "job.title_placeholder": {
        "ru": "напр. Токарь 5 разряда", "uz_latin": "masalan, 5-toifali tokar", "uz_cyrillic": "масалан, 5-тоифали токар",
        "en": "e.g. Lathe operator, grade 5",
    },
    "job.profession_required": {
        "ru": "Профессия *", "uz_latin": "Kasb *", "uz_cyrillic": "Касб *", "en": "Profession *",
    },
    "job.description_field": {
        "ru": "Описание, требования, условия *", "uz_latin": "Tavsif, talablar, shartlar *",
        "uz_cyrillic": "Тавсиф, талаблар, шартлар *", "en": "Description, requirements, terms *",
    },
    "job.employment_type": {
        "ru": "Тип занятости *", "uz_latin": "Bandlik turi *", "uz_cyrillic": "Бандлик тури *",
        "en": "Employment type *",
    },
    "job.full_time": {
        "ru": "Полная занятость", "uz_latin": "Toʻliq bandlik", "uz_cyrillic": "Тўлиқ бандлик",
        "en": "Full time",
    },
    "job.part_time": {
        "ru": "Частичная занятость", "uz_latin": "Qisman bandlik", "uz_cyrillic": "Қисман бандлик",
        "en": "Part time",
    },
    "job.shift": {
        "ru": "Вахта/смена", "uz_latin": "Vaxta/smena", "uz_cyrillic": "Вахта/смена", "en": "Shift work",
    },
    "job.contract": {
        "ru": "Контракт/подряд", "uz_latin": "Shartnoma/pudrat", "uz_cyrillic": "Шартнома/пудрат",
        "en": "Contract",
    },
    "job.salary_from": {
        "ru": "Зарплата от", "uz_latin": "Ish haqi dan", "uz_cyrillic": "Иш ҳақи дан", "en": "Salary from",
    },
    "job.salary_to": {
        "ru": "Зарплата до", "uz_latin": "Ish haqi gacha", "uz_cyrillic": "Иш ҳақи гача", "en": "Salary to",
    },
    "job.publish_vacancy": {
        "ru": "Опубликовать вакансию", "uz_latin": "Ish oʻrnini eʼlon qilish", "uz_cyrillic": "Иш ўрнини эълон қилиш",
        "en": "Publish job",
    },
    "job.write_to_employer": {
        "ru": "✉ Написать работодателю", "uz_latin": "✉ Ish beruvchiga yozish", "uz_cyrillic": "✉ Иш берувчига ёзиш",
        "en": "✉ Message the employer",
    },
    "job.responses_section": {
        "ru": "Отклики ({count})", "uz_latin": "Takliflar ({count})", "uz_cyrillic": "Таклифлар ({count})",
        "en": "Responses ({count})",
    },
    "job.no_responses": {
        "ru": "Откликов пока нет.", "uz_latin": "Hozircha takliflar yoʻq.", "uz_cyrillic": "Ҳозирча таклифлар йўқ.",
        "en": "No responses yet.",
    },
    "job.already_applied": {
        "ru": "Вы уже откликнулись на эту вакансию.", "uz_latin": "Siz bu ish oʻrniga allaqachon murojaat qilgansiz.",
        "uz_cyrillic": "Сиз бу иш ўрнига аллақачон мурожаат қилгансиз.", "en": "You've already applied to this job.",
    },
    "job.respond_section": {
        "ru": "Откликнуться", "uz_latin": "Murojaat qilish", "uz_cyrillic": "Мурожаат қилиш", "en": "Apply",
    },
    "job.cover_message": {
        "ru": "Сопроводительное сообщение", "uz_latin": "Qoʻshimcha xabar", "uz_cyrillic": "Қўшимча хабар",
        "en": "Cover message",
    },
    "job.apply_btn": {
        "ru": "Откликнуться", "uz_latin": "Murojaat qilish", "uz_cyrillic": "Мурожаат қилиш", "en": "Apply",
    },
    "resume.title": {
        "ru": "Резюме", "uz_latin": "Rezyume", "uz_cyrillic": "Резюме", "en": "Resumes",
    },
    "resume.candidates_title": {
        "ru": "Резюме соискателей", "uz_latin": "Nomzodlar rezyumelari", "uz_cyrillic": "Номзодлар резюмелари",
        "en": "Candidate resumes",
    },
    "resume.my_resume": {
        "ru": "Моё резюме", "uz_latin": "Mening rezyumem", "uz_cyrillic": "Менинг резюмем", "en": "My resume",
    },
    "resume.table_experience": {
        "ru": "Опыт", "uz_latin": "Tajriba", "uz_cyrillic": "Тажриба", "en": "Experience",
    },
    "resume.table_salary_expectation": {
        "ru": "Ожидания по зарплате", "uz_latin": "Ish haqi kutilmalari", "uz_cyrillic": "Иш ҳақи кутилмалари",
        "en": "Salary expectation",
    },
    "resume.years_short": {
        "ru": "{value} лет", "uz_latin": "{value} yil", "uz_cyrillic": "{value} йил", "en": "{value} years",
    },
    "resume.no_resumes": {
        "ru": "Пока нет резюме по этим фильтрам.", "uz_latin": "Bu filtrlar boʻyicha rezyumelar hozircha yoʻq.",
        "uz_cyrillic": "Бу фильтрлар бўйича резюмелар ҳозирча йўқ.", "en": "No resumes match these filters yet.",
    },
    "resume.about_skills": {
        "ru": "О себе, навыки, с каким оборудованием умеете работать *",
        "uz_latin": "O‘zingiz haqingizda, koʻnikmalar, qanday uskunalarda ishlay olasiz *",
        "uz_cyrillic": "Ўзингиз ҳақингизда, кўникмалар, қандай ускуналарда ишлай оласиз *",
        "en": "About you, skills, what equipment you can operate *",
    },
    "resume.expected_salary": {
        "ru": "Ожидаемая зарплата", "uz_latin": "Kutilayotgan ish haqi", "uz_cyrillic": "Кутилаётган иш ҳақи",
        "en": "Expected salary",
    },
    "resume.update": {
        "ru": "Обновить резюме", "uz_latin": "Rezyumeni yangilash", "uz_cyrillic": "Резюмени янгилаш",
        "en": "Update resume",
    },
    "resume.publish": {
        "ru": "Опубликовать резюме", "uz_latin": "Rezyumeni eʼlon qilish", "uz_cyrillic": "Резюмени эълон қилиш",
        "en": "Publish resume",
    },
    "resume.write_to_candidate": {
        "ru": "✉ Написать кандидату", "uz_latin": "✉ Nomzodga yozish", "uz_cyrillic": "✉ Номзодга ёзиш",
        "en": "✉ Message the candidate",
    },
    "resume.experience_label": {
        "ru": "Опыт: {value} лет", "uz_latin": "Tajriba: {value} yil", "uz_cyrillic": "Тажриба: {value} йил",
        "en": "Experience: {value} years",
    },
    "resume.expectations_label": {
        "ru": "Ожидания: {value}", "uz_latin": "Kutilmalar: {value}", "uz_cyrillic": "Кутилмалар: {value}",
        "en": "Expects: {value}",
    },
    "resume.invites_section": {
        "ru": "Приглашения от работодателей ({count})", "uz_latin": "Ish beruvchilardan takliflar ({count})",
        "uz_cyrillic": "Иш берувчилардан таклифлар ({count})", "en": "Invitations from employers ({count})",
    },
    "resume.no_invites": {
        "ru": "Приглашений пока нет.", "uz_latin": "Hozircha takliflar yoʻq.", "uz_cyrillic": "Ҳозирча таклифлар йўқ.",
        "en": "No invitations yet.",
    },
    "resume.already_invited": {
        "ru": "Вы уже приглашали этого кандидата.", "uz_latin": "Siz bu nomzodni allaqachon taklif qilgansiz.",
        "uz_cyrillic": "Сиз бу номзодни аллақачон таклиф қилгансиз.", "en": "You've already invited this candidate.",
    },
    "resume.invite_section": {
        "ru": "Пригласить", "uz_latin": "Taklif qilish", "uz_cyrillic": "Таклиф қилиш", "en": "Invite",
    },
    "resume.invite_message_placeholder": {
        "ru": "Расскажите о вакансии", "uz_latin": "Ish oʻrni haqida gapirib bering", "uz_cyrillic": "Иш ўрни ҳақида гапириб беринг",
        "en": "Tell them about the job",
    },
    "resume.invite_btn": {
        "ru": "Пригласить", "uz_latin": "Taklif qilish", "uz_cyrillic": "Таклиф қилиш", "en": "Invite",
    },
    "chat.messages_title": {
        "ru": "Сообщения", "uz_latin": "Xabarlar", "uz_cyrillic": "Хабарлар", "en": "Messages",
    },
    "chat.you_prefix": {
        "ru": "Вы:", "uz_latin": "Siz:", "uz_cyrillic": "Сиз:", "en": "You:",
    },
    "chat.no_conversations": {
        "ru": "Пока нет ни одного диалога. Написать можно любому пользователю — например, автору объявления или исполнителю с карты.",
        "uz_latin": "Hozircha birorta ham suhbat yoʻq. Har qanday foydalanuvchiga yozishingiz mumkin — masalan, eʼlon muallifiga yoki xaritadagi ijrochiga.",
        "uz_cyrillic": "Ҳозирча бирорта ҳам суҳбат йўқ. Ҳар қандай фойдаланувчига ёзишингиз мумкин — масалан, эълон муаллифига ёки харитадаги ижрочига.",
        "en": "No conversations yet. You can message any user — e.g. a listing author or an executor from the map.",
    },
    "chat.dialog_with": {
        "ru": "Диалог с {email}", "uz_latin": "{email} bilan suhbat", "uz_cyrillic": "{email} билан суҳбат",
        "en": "Chat with {email}",
    },
    "chat.all_messages": {
        "ru": "← Все сообщения", "uz_latin": "← Barcha xabarlar", "uz_cyrillic": "← Барча хабарлар",
        "en": "← All messages",
    },
    "chat.discussing_order": {
        "ru": "Обсуждаете заявку", "uz_latin": "Muhokama qilinayotgan buyurtma", "uz_cyrillic": "Муҳокама қилинаётган буюртма",
        "en": "Discussing order",
    },
    "chat.no_messages_yet": {
        "ru": "Сообщений пока нет — напишите первым.", "uz_latin": "Hozircha xabarlar yoʻq — birinchi boʻlib yozing.",
        "uz_cyrillic": "Ҳозирча хабарлар йўқ — биринчи бўлиб ёзинг.", "en": "No messages yet — be the first to write.",
    },
    "chat.message_field": {
        "ru": "Сообщение", "uz_latin": "Xabar", "uz_cyrillic": "Хабар", "en": "Message",
    },
    "chat.message_order_prefix": {
        "ru": "По заявке №{id}: ", "uz_latin": "№{id} buyurtma boʻyicha: ", "uz_cyrillic": "№{id} буюртма бўйича: ",
        "en": "Regarding order #{id}: ",
    },
    "chat.send": {
        "ru": "Отправить", "uz_latin": "Yuborish", "uz_cyrillic": "Юбориш", "en": "Send",
    },
    "search.title": {
        "ru": "Поиск по сайту", "uz_latin": "Sayt boʻyicha qidiruv", "uz_cyrillic": "Сайт бўйича қидирув",
        "en": "Site search",
    },
    "search.hint": {
        "ru": "Ищет среди исполнителей, конструкторов, барахолки станков, материалов и вакансий.",
        "uz_latin": "Ijrochilar, konstruktorlar, stanoklar bozorchasi, materiallar va ish oʻrinlari orasida qidiradi.",
        "uz_cyrillic": "Ижрочилар, конструкторлар, станоклар бозорчаси, материаллар ва иш ўринлари орасида қидиради.",
        "en": "Searches among executors, designers, equipment marketplace, materials and jobs.",
    },
    "search.query_label": {
        "ru": "Запрос", "uz_latin": "Soʻrov", "uz_cyrillic": "Сўров", "en": "Query",
    },
    "search.query_placeholder": {
        "ru": "например, токарный станок", "uz_latin": "masalan, tokarlik stanogi", "uz_cyrillic": "масалан, токарлик станоги",
        "en": "e.g. lathe",
    },
    "search.match_mode": {
        "ru": "Совпадение", "uz_latin": "Moslik", "uz_cyrillic": "Мослик", "en": "Match",
    },
    "search.match_partial": {
        "ru": "Частичное (содержит)", "uz_latin": "Qisman (ichida bor)", "uz_cyrillic": "Қисман (ичида бор)",
        "en": "Partial (contains)",
    },
    "search.match_exact": {
        "ru": "Точное (полное совпадение)", "uz_latin": "Aniq (toʻliq moslik)", "uz_cyrillic": "Аниқ (тўлиқ мослик)",
        "en": "Exact (full match)",
    },
    "search.search_btn": {
        "ru": "Искать", "uz_latin": "Qidirish", "uz_cyrillic": "Қидириш", "en": "Search",
    },
    "search.no_results": {
        "ru": "По запросу «{q}» ({mode}) ничего не найдено.", "uz_latin": "«{q}» soʻrovi ({mode}) boʻyicha hech narsa topilmadi.",
        "uz_cyrillic": "«{q}» сўрови ({mode}) бўйича ҳеч нарса топилмади.", "en": "No results for \"{q}\" ({mode}).",
    },
    "search.mode_exact_label": {
        "ru": "точное совпадение", "uz_latin": "aniq mos kelish", "uz_cyrillic": "аниқ мос келиш",
        "en": "exact match",
    },
    "search.mode_partial_label": {
        "ru": "частичное совпадение", "uz_latin": "qisman mos kelish", "uz_cyrillic": "қисман мос келиш",
        "en": "partial match",
    },
    "search.section_executors": {
        "ru": "Исполнители", "uz_latin": "Ijrochilar", "uz_cyrillic": "Ижрочилар", "en": "Executors",
    },
    "search.section_constructors": {
        "ru": "Конструкторы", "uz_latin": "Konstruktorlar", "uz_cyrillic": "Конструкторлар", "en": "Designers",
    },
    "search.section_listings": {
        "ru": "Барахолка станков и инструмента", "uz_latin": "Stanoklar va asboblar bozorchasi",
        "uz_cyrillic": "Станоклар ва асбоблар бозорчаси", "en": "Machines and tools marketplace",
    },
    "search.section_materials": {
        "ru": "Материалы и сырьё", "uz_latin": "Materiallar va xomashyo", "uz_cyrillic": "Материаллар ва хомашё",
        "en": "Materials and raw stock",
    },
    "search.section_vacancies": {
        "ru": "Вакансии", "uz_latin": "Ish oʻrinlari", "uz_cyrillic": "Иш ўринлари", "en": "Jobs",
    },
    "map.title": {
        "ru": "Карта изготовителей, продавцов и конструкторов",
        "uz_latin": "Ishlab chiqaruvchilar, sotuvchilar va konstruktorlar xaritasi",
        "uz_cyrillic": "Ишлаб чиқарувчилар, сотувчилар ва конструкторлар харитаси",
        "en": "Map of manufacturers, sellers and designers",
    },
    "map.who_to_show": {
        "ru": "Кого показать", "uz_latin": "Kimni koʻrsatish", "uz_cyrillic": "Кимни кўрсатиш", "en": "Who to show",
    },
    "map.sellers": {
        "ru": "Продавцы (барахолка)", "uz_latin": "Sotuvchilar (bozorcha)", "uz_cyrillic": "Сотувчилар (бозорча)",
        "en": "Sellers (marketplace)",
    },
    "map.executors": {
        "ru": "Исполнители", "uz_latin": "Ijrochilar", "uz_cyrillic": "Ижрочилар", "en": "Executors",
    },
    "map.constructors": {
        "ru": "Конструкторы", "uz_latin": "Konstruktorlar", "uz_cyrillic": "Конструкторлар", "en": "Designers",
    },
    "map.service_category_filter": {
        "ru": "Категория услуг (для исполнителей)", "uz_latin": "Xizmat toifasi (ijrochilar uchun)",
        "uz_cyrillic": "Хизмат тоифаси (ижрочилар учун)", "en": "Service category (for executors)",
    },
    "map.org_type_filter": {
        "ru": "Тип организации (для исполнителей)", "uz_latin": "Tashkilot turi (ijrochilar uchun)",
        "uz_cyrillic": "Ташкилот тури (ижрочилар учун)", "en": "Organization type (for executors)",
    },
    "map.has_designer_filter": {
        "ru": "Есть конструктор в штате (для исполнителей)", "uz_latin": "Shtatda konstruktor bor (ijrochilar uchun)",
        "uz_cyrillic": "Штатда конструктор бор (ижрочилар учун)", "en": "Has in-house designer (for executors)",
    },
    "map.show_nearby": {
        "ru": "📍 Показать рядом со мной", "uz_latin": "📍 Mening atrofimda koʻrsatish", "uz_cyrillic": "📍 Менинг атрофимда кўрсатиш",
        "en": "📍 Show near me",
    },
    "map.manual_pin": {
        "ru": "✋ Указать себя на карте", "uz_latin": "✋ Xaritada oʻzimni belgilash", "uz_cyrillic": "✋ Харитада ўзимни белгилаш",
        "en": "✋ Place my pin on the map",
    },
    "map.manual_pin_hint": {
        "ru": "Кликните на карту, чтобы отметить, где вы находитесь.",
        "uz_latin": "Qayerda ekanligingizni belgilash uchun xaritani bosing.",
        "uz_cyrillic": "Қаерда эканлигингизни белгилаш учун харитани босинг.",
        "en": "Click the map to mark where you are.",
    },
    "map.nearby_section": {
        "ru": "Ближайшие", "uz_latin": "Eng yaqinlar", "uz_cyrillic": "Энг яқинлар", "en": "Nearby",
    },
    "review.leave_title": {
        "ru": "Оставить отзыв", "uz_latin": "Sharh qoldirish", "uz_cyrillic": "Шарҳ қолдириш",
        "en": "Leave a review",
    },
    "review.about_order": {
        "ru": "Отзыв о заказе «{title}»", "uz_latin": "«{title}» buyurtmasi haqida sharh",
        "uz_cyrillic": "«{title}» буюртмаси ҳақида шарҳ", "en": "Review for order \"{title}\"",
    },
    "review.rating_field": {
        "ru": "Оценка (1–5) *", "uz_latin": "Baho (1–5) *", "uz_cyrillic": "Баҳо (1–5) *", "en": "Rating (1–5) *",
    },
    "review.comment_field": {
        "ru": "Комментарий", "uz_latin": "Izoh", "uz_cyrillic": "Изоҳ", "en": "Comment",
    },
    "review.update": {
        "ru": "Обновить отзыв", "uz_latin": "Sharhni yangilash", "uz_cyrillic": "Шарҳни янгилаш",
        "en": "Update review",
    },
    "review.submit": {
        "ru": "Отправить отзыв", "uz_latin": "Sharhni yuborish", "uz_cyrillic": "Шарҳни юбориш",
        "en": "Submit review",
    },
    "review.pending_publish": {
        "ru": "Ваш отзыв сохранён и будет опубликован, как только своё мнение оставит другая сторона.",
        "uz_latin": "Sharhingiz saqlandi va boshqa tomon fikrini bildirishi bilan eʼlon qilinadi.",
        "uz_cyrillic": "Шарҳингиз сақланди ва бошқа томон фикрини билдириши билан эълон қилинади.",
        "en": "Your review is saved and will be published once the other side leaves theirs.",
    },
    "review.title": {
        "ru": "Отзывы", "uz_latin": "Sharhlar", "uz_cyrillic": "Шарҳлар", "en": "Reviews",
    },
    "review.received": {
        "ru": "Полученные", "uz_latin": "Olingan", "uz_cyrillic": "Олинган", "en": "Received",
    },
    "review.no_received": {
        "ru": "Пока нет опубликованных отзывов о вас.", "uz_latin": "Sizga hali eʼlon qilingan sharhlar yoʻq.",
        "uz_cyrillic": "Сизга ҳали эълон қилинган шарҳлар йўқ.", "en": "No published reviews about you yet.",
    },
    "review.given": {
        "ru": "Оставленные вами", "uz_latin": "Siz qoldirgan", "uz_cyrillic": "Сиз қолдирган",
        "en": "Left by you",
    },
    "review.no_given": {
        "ru": "Вы ещё не оставляли отзывов.", "uz_latin": "Siz hali sharh qoldirmagansiz.",
        "uz_cyrillic": "Сиз ҳали шарҳ қолдирмагансиз.", "en": "You haven't left any reviews yet.",
    },
    "review.pending_badge": {
        "ru": "(ожидает публикации)", "uz_latin": "(eʼlon qilinishini kutmoqda)", "uz_cyrillic": "(эълон қилинишини кутмоқда)",
        "en": "(awaiting publication)",
    },
    "review.order_meta": {
        "ru": "заказ «{title}»", "uz_latin": "«{title}» buyurtmasi", "uz_cyrillic": "«{title}» буюртмаси",
        "en": "order \"{title}\"",
    },
    "dispute.status_open": {
        "ru": "открыт", "uz_latin": "ochiq", "uz_cyrillic": "очиқ", "en": "open",
    },
    "dispute.status_evidence_collection": {
        "ru": "сбор доказательств", "uz_latin": "dalillar yigʻilmoqda", "uz_cyrillic": "далиллар йиғилмоқда",
        "en": "collecting evidence",
    },
    "dispute.status_in_review": {
        "ru": "на рассмотрении", "uz_latin": "koʻrib chiqilmoqda", "uz_cyrillic": "кўриб чиқилмоқда",
        "en": "under review",
    },
    "dispute.status_resolved_customer": {
        "ru": "решено в пользу заказчика", "uz_latin": "buyurtmachi foydasiga hal qilindi",
        "uz_cyrillic": "буюртмачи фойдасига ҳал қилинди", "en": "resolved for customer",
    },
    "dispute.status_resolved_executor": {
        "ru": "решено в пользу исполнителя", "uz_latin": "ijrochi foydasiga hal qilindi",
        "uz_cyrillic": "ижрочи фойдасига ҳал қилинди", "en": "resolved for executor",
    },
    "dispute.status_resolved_partial": {
        "ru": "частичное решение", "uz_latin": "qisman hal qilindi", "uz_cyrillic": "қисман ҳал қилинди",
        "en": "partially resolved",
    },
    "dispute.reason_defect": {
        "ru": "Брак", "uz_latin": "Nuqson", "uz_cyrillic": "Нуқсон", "en": "Defect",
    },
    "dispute.reason_delay": {
        "ru": "Задержка сроков", "uz_latin": "Muddat kechikishi", "uz_cyrillic": "Муддат кечикиши",
        "en": "Delay",
    },
    "dispute.reason_quality": {
        "ru": "Претензия по качеству", "uz_latin": "Sifat boʻyicha da’vo", "uz_cyrillic": "Сифат бўйича даъво",
        "en": "Quality complaint",
    },
    "dispute.reason_price_dispute": {
        "ru": "Расхождение по цене", "uz_latin": "Narx boʻyicha kelishmovchilik", "uz_cyrillic": "Нарх бўйича келишмовчилик",
        "en": "Price disagreement",
    },
    "dispute.reason_other": {
        "ru": "Другое", "uz_latin": "Boshqa", "uz_cyrillic": "Бошқа", "en": "Other",
    },
    "dispute.open_title": {
        "ru": "Открыть спор", "uz_latin": "Nizo ochish", "uz_cyrillic": "Низо очиш", "en": "Open dispute",
    },
    "dispute.about_order": {
        "ru": "Спор по заказу «{title}»", "uz_latin": "«{title}» buyurtmasi boʻyicha nizo",
        "uz_cyrillic": "«{title}» буюртмаси бўйича низо", "en": "Dispute for order \"{title}\"",
    },
    "dispute.describe_hint": {
        "ru": "Опишите проблему и после отправки приложите фото/видео-доказательства — это поможет администратору объективно разобраться.",
        "uz_latin": "Muammoni tasvirlang va yuborgandan keyin foto/video-dalillarni ilova qiling — bu administratorga adolatli hal qilishga yordam beradi.",
        "uz_cyrillic": "Муаммони тасвирланг ва юборгандан кейин фото/видео-далилларни илова қилинг — бу администраторга адолатли ҳал қилишга ёрдам беради.",
        "en": "Describe the problem, and after submitting attach photo/video evidence — this helps the admin resolve it fairly.",
    },
    "dispute.reason_field": {
        "ru": "Причина *", "uz_latin": "Sabab *", "uz_cyrillic": "Сабаб *", "en": "Reason *",
    },
    "dispute.describe_situation": {
        "ru": "Опишите ситуацию *", "uz_latin": "Vaziyatni tasvirlang *", "uz_cyrillic": "Вазиятни тасвирланг *",
        "en": "Describe the situation *",
    },
    "dispute.short_title": {
        "ru": "Спор: «{title}»", "uz_latin": "Nizo: «{title}»", "uz_cyrillic": "Низо: «{title}»",
        "en": "Dispute: \"{title}\"",
    },
    "dispute.reason_meta": {
        "ru": "Причина: {value}", "uz_latin": "Sabab: {value}", "uz_cyrillic": "Сабаб: {value}",
        "en": "Reason: {value}",
    },
    "dispute.opened_meta": {
        "ru": "Открыт: {email}, {date}", "uz_latin": "Ochilgan: {email}, {date}", "uz_cyrillic": "Очилган: {email}, {date}",
        "en": "Opened: {email}, {date}",
    },
    "dispute.admin_resolution": {
        "ru": "Решение администратора ({status}):", "uz_latin": "Administrator qarori ({status}):",
        "uz_cyrillic": "Администратор қарори ({status}):", "en": "Admin resolution ({status}):",
    },
    "dispute.evidence_title": {
        "ru": "Доказательства", "uz_latin": "Dalillar", "uz_cyrillic": "Далиллар", "en": "Evidence",
    },
    "dispute.evidence_alt": {
        "ru": "доказательство", "uz_latin": "dalil", "uz_cyrillic": "далил", "en": "evidence",
    },
    "dispute.no_evidence": {
        "ru": "Доказательств пока нет.", "uz_latin": "Hozircha dalillar yoʻq.", "uz_cyrillic": "Ҳозирча далиллар йўқ.",
        "en": "No evidence yet.",
    },
    "dispute.evidence_file_label": {
        "ru": "Фото/видео (изображение)", "uz_latin": "Foto/video (rasm)", "uz_cyrillic": "Фото/видео (расм)",
        "en": "Photo/video (image)",
    },
    "dispute.comment_field": {
        "ru": "Комментарий", "uz_latin": "Izoh", "uz_cyrillic": "Изоҳ", "en": "Comment",
    },
    "dispute.add_evidence": {
        "ru": "Добавить доказательство", "uz_latin": "Dalil qoʻshish", "uz_cyrillic": "Далил қўшиш",
        "en": "Add evidence",
    },
    "dispute.ready_for_review": {
        "ru": "Готово к рассмотрению →", "uz_latin": "Koʻrib chiqishga tayyor →", "uz_cyrillic": "Кўриб чиқишга тайёр →",
        "en": "Ready for review →",
    },
    "dispute.conversation_title": {
        "ru": "Переписка", "uz_latin": "Yozishmalar", "uz_cyrillic": "Ёзишмалар", "en": "Conversation",
    },
    "dispute.internal_note_badge": {
        "ru": "(внутренняя заметка)", "uz_latin": "(ichki eslatma)", "uz_cyrillic": "(ички эслатма)",
        "en": "(internal note)",
    },
    "dispute.message_field": {
        "ru": "Сообщение", "uz_latin": "Xabar", "uz_cyrillic": "Хабар", "en": "Message",
    },
    "dispute.internal_note_checkbox": {
        "ru": "Внутренняя заметка (не видна сторонам)", "uz_latin": "Ichki eslatma (tomonlarga koʻrinmaydi)",
        "uz_cyrillic": "Ички эслатма (томонларга кўринмайди)", "en": "Internal note (not visible to parties)",
    },
    "dispute.admin_resolution_title": {
        "ru": "Решение администратора", "uz_latin": "Administrator qarori", "uz_cyrillic": "Администратор қарори",
        "en": "Admin resolution",
    },
    "dispute.resolution_favor": {
        "ru": "В чью пользу решение *", "uz_latin": "Kim foydasiga qaror *", "uz_cyrillic": "Ким фойдасига қарор *",
        "en": "In whose favor *",
    },
    "dispute.favor_customer": {
        "ru": "В пользу заказчика", "uz_latin": "Buyurtmachi foydasiga", "uz_cyrillic": "Буюртмачи фойдасига",
        "en": "In favor of customer",
    },
    "dispute.favor_executor": {
        "ru": "В пользу исполнителя", "uz_latin": "Ijrochi foydasiga", "uz_cyrillic": "Ижрочи фойдасига",
        "en": "In favor of executor",
    },
    "dispute.favor_partial": {
        "ru": "Частично / компромисс", "uz_latin": "Qisman / kelishuv", "uz_cyrillic": "Қисман / келишув",
        "en": "Partial / compromise",
    },
    "dispute.resolution_justification": {
        "ru": "Обоснование *", "uz_latin": "Asoslash *", "uz_cyrillic": "Асослаш *", "en": "Justification *",
    },
    "dispute.final_order_status": {
        "ru": "Итоговый статус заказа *", "uz_latin": "Buyurtmaning yakuniy holati *",
        "uz_cyrillic": "Буюртманинг якуний ҳолати *", "en": "Final order status *",
    },
    "dispute.make_resolution": {
        "ru": "Вынести решение", "uz_latin": "Qaror chiqarish", "uz_cyrillic": "Қарор чиқариш",
        "en": "Issue resolution",
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


def order_status_label(status):
    if not status:
        return status
    return translate(f"order.status_{status}")


def bid_status_label(status):
    if not status:
        return status
    return translate(f"bid.status_{status}")


LISTING_STATUS_KEYS = {"active": "listing.status_active", "reserved": "listing.status_reserved", "closed": "listing.status_closed"}


def listing_status_label(status):
    key = LISTING_STATUS_KEYS.get(status)
    return translate(key) if key else status


def dispute_status_label(status):
    if not status:
        return status
    return translate(f"dispute.status_{status}")


def dispute_reason_label(reason):
    if not reason:
        return reason
    return translate(f"dispute.reason_{reason}")


def register_i18n(app):
    @app.context_processor
    def inject_i18n():
        return {
            "current_lang": get_current_lang(),
            "supported_languages": SUPPORTED_LANGUAGES,
            "language_labels": LANGUAGE_LABELS,
        }

    app.jinja_env.globals["t"] = translate
    app.jinja_env.globals["order_status_label"] = order_status_label
    app.jinja_env.globals["bid_status_label"] = bid_status_label
    app.jinja_env.globals["listing_status_label"] = listing_status_label
    app.jinja_env.globals["dispute_status_label"] = dispute_status_label
    app.jinja_env.globals["dispute_reason_label"] = dispute_reason_label


def get_current_lang():
    if current_user.is_authenticated and current_user.preferred_language in SUPPORTED_LANGUAGES:
        return current_user.preferred_language
    lang = session.get("lang")
    if lang in SUPPORTED_LANGUAGES:
        return lang
    return "ru"
