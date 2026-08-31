# Публикация «Как стать миллиардером» в Google Play и RuStore

Это Android-приложение — обёртка (Capacitor) над тем же квестом, что уже есть
на сайте (`projects/millionaire-quest`), плюс переключатель языка RU/EN и
подготовленные иконки/сплэш-скрин. Приложение полностью офлайн: все квесты,
пароли (в виде SHA-256-хешей) и прогресс хранятся локально на устройстве
(localStorage), интернет не используется, разрешение `INTERNET` не запрашивается.

Ниже — пошаговая инструкция, что нужно сделать **вам** (шаги, требующие
входа в ваш аккаунт разработчика, оплаты и т.п.), и что уже сделано.

## Что уже готово в этом репозитории

- `mobile-app/millionaire-quest/www/` — локализованные страницы приложения
  (index/editor/player) с переключателем 🇷🇺/🇬🇧 в правом верхнем углу
  (`i18n.js`).
- `mobile-app/millionaire-quest/android/` — нативный Android-проект
  (Capacitor), уже собирается (`assembleDebug` и `bundleRelease` проверены).
- Иконка приложения и адаптивная иконка (`android/app/src/main/res/mipmap-*`),
  сплэш-скрин (`android/app/src/main/res/drawable*/splash.png`).
- `store-assets/icon-512.png` и `store-assets/feature-graphic-1024x500.png`
  для карточки в Google Play.
- `projects/millionaire-quest/privacy-policy.html` — двуязычная (RU/EN)
  политика конфиденциальности. После деплоя сайта будет доступна по адресу
  `https://www.robutpit.com/projects/millionaire-quest/privacy-policy.html`.
  **Перед публикацией замените `YOUR_EMAIL@example.com` в этом файле на
  реальный контактный email** (оба языковых блока).
- `STORE_LISTING.md` — готовые тексты карточки приложения на RU и EN.

Package name (applicationId): `com.robutpit.millionairequest`
App name: RU — «Как стать миллиардером», EN — «Millionaire Quest»
(подставляется автоматически по языку системы через `values`/`values-en`).

## 1. Подпишите релизную сборку (обязательно перед публикацией)

Google Play и RuStore принимают только подписанные сборки. Ключ подписи —
это ваш секрет, я не создаю и не храню его в репозитории.

```bash
cd mobile-app/millionaire-quest/android
keytool -genkeypair -v -keystore release.keystore -alias millionaire-quest \
  -keyalg RSA -keysize 2048 -validity 10000
```

Сохраните `release.keystore` и пароли в надёжном месте (менеджер паролей).
**Если потеряете этот ключ — не сможете выпускать обновления того же
приложения**, придётся публиковать новое.

Создайте файл `android/key.properties` (он уже в `.gitignore`, в git не
попадёт):

```
storeFile=release.keystore
storePassword=ВАШ_ПАРОЛЬ_ХРАНИЛИЩА
keyAlias=millionaire-quest
keyPassword=ВАШ_ПАРОЛЬ_КЛЮЧА
```

Добавьте в `android/app/build.gradle` перед блоком `android {`:

```groovy
def keystoreProperties = new Properties()
def keystorePropertiesFile = rootProject.file('key.properties')
if (keystorePropertiesFile.exists()) {
    keystoreProperties.load(new FileInputStream(keystorePropertiesFile))
}
```

И внутри `android { ... }` добавьте `signingConfigs` и подключите его к
`buildTypes.release`:

```groovy
signingConfigs {
    release {
        if (keystorePropertiesFile.exists()) {
            storeFile file(keystoreProperties['storeFile'])
            storePassword keystoreProperties['storePassword']
            keyAlias keystoreProperties['keyAlias']
            keyPassword keystoreProperties['keyPassword']
        }
    }
}
buildTypes {
    release {
        signingConfig signingConfigs.release
        minifyEnabled false
        proguardFiles getDefaultProguardFile('proguard-android.txt'), 'proguard-rules.pro'
    }
}
```

## 2. Соберите релизные файлы

```bash
cd mobile-app/millionaire-quest
npm install
npx cap sync android
cd android
./gradlew bundleRelease   # .aab для Google Play
./gradlew assembleRelease # .apk (пригодится для RuStore и ручного тестирования)
```

Файлы появятся здесь:
- `android/app/build/outputs/bundle/release/app-release.aab`
- `android/app/build/outputs/apk/release/app-release.apk`

Перед сборкой релиза стоит поднять номер версии в
`android/app/build.gradle` (`versionCode` и `versionName`) — сейчас
`versionCode 1`, `versionName "1.0"`.

## 3. Проверьте приложение перед публикацией

Установите debug-сборку на телефон или эмулятор и пройдите весь путь:
создание квеста, экспорт/импорт JSON, прохождение демо-квеста, переключение
языка RU↔EN.

```bash
adb install android/app/build/outputs/apk/debug/app-debug.apk
```

## 4. Google Play Console

1. Зарегистрируйтесь как разработчик на https://play.google.com/console
   (разовый взнос ~25 USD).
2. Create app → укажите название («Как стать миллиардером» / «Millionaire
   Quest»), язык по умолчанию, «Игра», бесплатное.
3. Store listing (заполните для RU и EN — Play Console поддерживает
   несколько языков листинга):
   - короткое и полное описание — берите из `STORE_LISTING.md`;
   - иконка 512×512 — `store-assets/icon-512.png`;
   - Feature graphic 1024×500 — `store-assets/feature-graphic-1024x500.png`;
   - минимум 2 скриншота телефона (сделайте скриншоты меню, прохождения
     квеста и редактора — снимите их с эмулятора/устройства через
     `adb shell screencap` или Android Studio).
4. App content:
   - Privacy policy URL: ссылка на `privacy-policy.html` (см. выше);
   - Content rating questionnaire — квест без насилия/18+, отметьте «Все
     возрасты» / Everyone;
   - Data safety — укажите, что приложение **не собирает и не передаёт
     данные** (всё хранится только на устройстве, сети приложение не
     использует).
5. Production → Create release → загрузите `app-release.aab`, дождитесь
   проверки Play Integrity/подписи, заполните release notes на RU/EN.
6. Отправьте на проверку. Обычно занимает от нескольких часов до пары дней.

## 5. RuStore

1. Зарегистрируйтесь как разработчик в консоли RuStore:
   https://console.rustore.ru (для юр. лиц/ИП/самозанятых требования могут
   отличаться — уточните актуальные условия в консоли на момент публикации,
   RuStore периодически их меняет).
2. Создайте новое приложение, укажите package name
   `com.robutpit.millionairequest` (должен совпадать с тем, что зашито в
   `capacitor.config.json` и `android/app/build.gradle`).
3. Загрузите `app-release.apk` (или `.aab`, если консоль его поддерживает
   на момент публикации) — тот же файл, что и для Google Play, ключ подписи
   можно использовать один и тот же.
4. Заполните карточку (RuStore пока в основном ориентирован на русский
   язык, но можно добавить и английское описание, если консоль это
   позволяет) — тексты также в `STORE_LISTING.md`.
5. Укажите ту же ссылку на политику конфиденциальности и контактный email.
6. Отправьте на модерацию.

## Обновления в будущем

Чтобы изменить сам квест/интерфейс: правьте файлы в
`mobile-app/millionaire-quest/www/`, затем:

```bash
cd mobile-app/millionaire-quest
npx cap sync android
cd android && ./gradlew bundleRelease
```

Не забывайте увеличивать `versionCode` в `android/app/build.gradle` при
каждой новой загрузке в магазины — иначе они откажут в приёме сборки.
