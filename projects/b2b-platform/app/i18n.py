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
