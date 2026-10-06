# 🌐 PitBrowser

Свой браузер для компьютера и телефона.

| Платформа | Папка | Технология | Движок |
|---|---|---|---|
| Windows, macOS, Linux | `desktop/` | Electron 44 | Chromium (встроен в приложение) |
| Android 7.0+ | `android/` | Kotlin, без сторонних библиотек | системный WebView (Chromium) |

Писать собственный движок отрисовки страниц нереально (это десятки миллионов строк кода), поэтому
PitBrowser, как Opera, Vivaldi, Brave и Яндекс Браузер, использует готовый движок Chromium, а всё
остальное — интерфейс, вкладки, закладки, история, загрузки, настройки — своё.

## Возможности

**Компьютер:** вкладки (перетаскивание, средняя кнопка мыши, восстановление закрытой), адресная строка
с подсказками из закладок и истории, выбор поисковика (Google, DuckDuckGo, Bing, Яндекс), панель
закладок, страницы `pit://history`, `pit://bookmarks`, `pit://downloads`, `pit://settings`, менеджер
загрузок, поиск по странице, масштаб, печать, «Сохранить как», приватные окна (данные в памяти и
удаляются при закрытии), запрос разрешений (камера, микрофон, геолокация, уведомления), контекстное меню,
светлая/тёмная тема, понятная страница ошибки.

**Телефон:** вкладки (сохраняются между запусками), адресная строка с подсказками, нижняя панель
навигации под большой палец, закладки и история (долгое нажатие — удалить/копировать/открыть в новой
вкладке), загрузки через системный менеджер, загрузка файлов на сайты, поиск по странице, «Поделиться»,
версия для ПК, полноэкранное видео, разрешения по запросу, блокировка всплывающих окон без нажатия,
открытие `tel:`, `mailto:`, `intent:` в других приложениях, можно выбрать браузером по умолчанию.

## Компьютер (`desktop/`)

Нужен Node.js 20+.

```bash
cd desktop
npm install
npm start          # запустить
npm test           # тесты адресной строки
npm run dist       # установщик для текущей ОС → desktop/dist/
```

- Windows: `PitBrowser Setup 1.0.0.exe` (установщик) и portable `.exe`
- macOS: `.dmg` (не подписан — при первом запуске: правый клик → «Открыть»)
- Linux: `.AppImage` и `.deb`

Устройство:

```
desktop/src/
  main.js          главный процесс: окна, вкладки (WebContentsView), меню, загрузки, разрешения
  omnibox.js       адрес или поиск — та же логика, что в android/.../Omnibox.kt
  store.js         закладки, история, настройки (JSON в папке профиля)
  ui/              панель: вкладки, адресная строка, меню, поиск по странице
  pages/           внутренние страницы pit://newtab, history, bookmarks, downloads, settings, error
  ui-preload.js    мост панель ↔ главный процесс
  page-preload.js  API только для страниц pit:// (обычные сайты его не видят)
```

## Телефон (`android/`)

Нужны JDK 17+ и Android SDK (проще всего открыть папку `android/` в Android Studio и нажать Run).

```bash
cd android
./gradlew testDebugUnitTest   # тесты адресной строки
./gradlew assembleRelease     # APK → app/build/outputs/apk/release/app-release.apk
```

Release-сборка сейчас подписывается отладочным ключом, чтобы APK можно было сразу поставить на
телефон. Для Google Play / IlovaBozor создайте свой ключ:

```bash
keytool -genkey -v -keystore pitbrowser.jks -keyalg RSA -keysize 2048 -validity 10000 -alias pitbrowser
```

и пропишите его в `android/app/build.gradle.kts` в `signingConfigs` (ключ в git не коммитить).

## Сборка всех версий в GitHub Actions

Workflow `.github/workflows/browser-build.yml` собирает Windows, macOS, Linux и Android.

- Вручную: Actions → **Build PitBrowser** → Run workflow — файлы появятся в артефактах запуска.
- Релиз: создайте тег `browser-v1.0.0` и запушьте его — установщики выложатся в GitHub Releases.

```bash
git tag browser-v1.0.0 && git push origin browser-v1.0.0
```

## Идеи для следующих версий

- блокировщик рекламы (списки EasyList)
- синхронизация закладок между компьютером и телефоном
- автообновление (electron-updater)
- iOS-версия (WKWebView, нужен Mac и аккаунт Apple Developer)
