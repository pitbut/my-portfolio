# Millionaire Quest — мобильное приложение (Android)

Мобильная версия квеста «Как стать миллиардером» с сайта
(`projects/millionaire-quest`), собранная как нативное Android-приложение
через [Capacitor](https://capacitorjs.com/). Полностью офлайн, без сервера
и без сбора данных — весь прогресс хранится локально на устройстве.

Поддерживаются два языка интерфейса — русский и английский, переключаются
кнопкой 🇷🇺/🇬🇧 в правом верхнем углу (запоминается на устройстве).

## Структура

```
mobile-app/millionaire-quest/
├── www/                  # веб-код приложения (то же, что на сайте + i18n)
│   ├── index.html         # меню
│   ├── editor.html        # редактор квестов
│   ├── player.html        # прохождение квеста
│   ├── i18n.js             # словарь RU/EN + переключатель языка
│   └── quests/demo.json    # демо-квест
├── android/               # нативный Android-проект (Capacitor)
├── store-assets/          # иконка 512×512, feature graphic, скриншоты
├── capacitor.config.json
├── STORE_LISTING.md       # готовые тексты карточки приложения (RU/EN)
└── PUBLISHING.md          # пошаговая инструкция публикации в Google Play и RuStore
```

## Быстрый старт (разработка)

```bash
cd mobile-app/millionaire-quest
npm install
npx cap sync android
cd android
./gradlew assembleDebug     # соберёт android/app/build/outputs/apk/debug/app-debug.apk
```

Установить на подключённое устройство/эмулятор:

```bash
adb install android/app/build/outputs/apk/debug/app-debug.apk
```

Открыть проект в Android Studio для отладки на эмуляторе:
`npx cap open android`.

## Публикация в Google Play / RuStore

См. **[PUBLISHING.md](./PUBLISHING.md)** — там пошагово расписано:
подписание релизной сборки собственным ключом, сборка `.aab`/`.apk`,
что заполнить в консолях магазинов, ссылка на политику конфиденциальности.

Готовые тексты для карточки приложения — в **[STORE_LISTING.md](./STORE_LISTING.md)**.

## Известные ограничения

- Демо-квест (`www/quests/demo.json`) остаётся на русском независимо от
  выбранного языка интерфейса — это пользовательские данные квеста, а не
  элемент интерфейса (так же, как и на сайте). Любой квест, который
  создаёт пользователь, будет на том языке, на котором его написали.
- Перед публикацией обязательно замените `YOUR_EMAIL@example.com` в
  `projects/millionaire-quest/privacy-policy.html` на реальный контактный
  email (см. PUBLISHING.md).
