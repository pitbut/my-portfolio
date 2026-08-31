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
  политика конфиденциальности с контактом gtnz1071980@gmail.com. После
  деплоя сайта будет доступна по адресу
  `https://www.robutpit.com/projects/millionaire-quest/privacy-policy.html`.
- `STORE_LISTING.md` — готовые тексты карточки приложения на RU и EN.

Package name (applicationId): `com.robutpit.millionairequest`
App name: RU — «Как стать миллиардером», EN — «Millionaire Quest»
(подставляется автоматически по языку системы через `values`/`values-en`).

## 1. Ключ подписи — уже создан, СОХРАНИТЕ ЕГО СЕБЕ

Google Play и RuStore принимают только подписанные сборки. Я сгенерировал
ключ и уже подписал им релизные файлы (см. раздел 2). Ключ лежит в
репозитории **локально в этой сессии**, но в git не закоммичен (он в
`.gitignore`) — заберите оба файла себе прямо сейчас, я отправлю их вам
отдельным сообщением:

- `android/release.keystore` — сам keystore-файл;
- `android/key.properties` — алиас и пароли к нему.

**Это критично: если вы потеряете эти файлы, вы никогда не сможете залить
обновление этого же приложения** ни в Google Play, ни в RuStore — обе
площадки требуют, чтобы все обновления были подписаны тем же ключом, что
и первая версия. Сохраните их в менеджере паролей / надёжном хранилище
(не просто в почте).

SHA-256 отпечаток сертификата (может понадобиться в консолях):
```
9b08e4498fac3e7c78015b5dab5b28c0b68e7615fb6ff085119bd790ce33df95
```

Если всё же захотите сгенерировать новый ключ сами:

```bash
cd mobile-app/millionaire-quest/android
keytool -genkeypair -v -keystore release.keystore -alias millionaire-quest \
  -keyalg RSA -keysize 2048 -validity 10000
```
и пропишите новые пароли в `android/key.properties` (формат уже настроен
в `android/app/build.gradle`, ничего в самом gradle-файле менять не нужно).

## 2. Готовые релизные файлы

Уже собраны и подписаны вашим ключом (см. отдельное сообщение с файлами):

- `android/app/build/outputs/bundle/release/app-release.aab` — **для Google
  Play** (Play принимает только AAB для новых приложений).
- `android/app/build/outputs/apk/release/app-release.apk` — **для RuStore**
  (RuStore принимает как APK, так и AAB; APK проще всего для ручной
  проверки на своём телефоне).

Чтобы пересобрать их самостоятельно после изменений:

```bash
cd mobile-app/millionaire-quest
npm install
npx cap sync android
cd android
./gradlew bundleRelease assembleRelease
```

Перед каждой новой отправкой в любой из магазинов поднимайте `versionCode`
и `versionName` в `android/app/build.gradle` (сейчас `versionCode 1`,
`versionName "1.0"`) — иначе площадка откажет в приёме файла как
дубликату версии.

## Требования к версии Android (SDK) — у площадок они разные

- **Google Play**: обязателен формат `.aab` для новых приложений;
  `targetSdkVersion` должен соответствовать актуальному требованию Google
  (обновляется примерно раз в год, для новых публикаций 2026 года — не
  ниже API 35). Сейчас в проекте `compileSdk`/`targetSdk` = **36**
  (см. `android/variables.gradle`) — это заведомо выше минимума, требование
  выполнено.
- **RuStore**: принимает `.apk` и `.aab`; исторически требования к
  `targetSdkVersion` у RuStore мягче и обновляются независимо от Google —
  на момент публикации сверьтесь с актуальным минимумом прямо в консоли
  RuStore (раздел требований к загружаемому файлу). `minSdkVersion = 24`
  (Android 7.0+) в этом проекте укладывается в требования обеих площадок.
- Если консоль одной из площадок потребует другой `targetSdkVersion`,
  меняется одна строка в `android/variables.gradle`
  (`targetSdkVersion = ...`), затем пересборка.

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
5. Production → Create release → загрузите готовый
   `android/app/build/outputs/bundle/release/app-release.aab`, дождитесь
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
3. Загрузите готовый
   `android/app/build/outputs/apk/release/app-release.apk`
   (или `.aab` из того же build, если консоль на момент публикации просит
   именно бандл) — ключ подписи тот же, что и для Google Play.
4. Заполните карточку (RuStore пока в основном ориентирован на русский
   язык, но можно добавить и английское описание, если консоль это
   позволяет) — тексты также в `STORE_LISTING.md`.
5. Укажите ту же ссылку на политику конфиденциальности и контакт
   gtnz1071980@gmail.com.
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
