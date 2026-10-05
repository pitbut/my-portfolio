# Колобок и Огненные башни

Аркада в духе Tower Toppler / Nebulus. Колобок катится вокруг вращающейся башни
и забирается на вершину, а снизу поднимается лава. Четыре башни: Зайца, Волка, Медведя и Лисы.

- `index.html` — вся игра в одном файле. Это и страница портфолио, и содержимое приложения.
- `android/` — Android-приложение (WebView), которое показывает тот же `index.html`.
- `store/` — иконка 512×512 и скриншоты для страницы в RuStore.

## Сборка APK

Нужны JDK 17+ и Android SDK (проще всего открыть папку `android/` в Android Studio).

```bash
cd android
./gradlew assembleDebug        # app/build/outputs/apk/debug/app-debug.apk, для проверки на телефоне
./gradlew assembleRelease      # app/build/outputs/apk/release/app-release.apk, для RuStore
```

При сборке `index.html` автоматически копируется в `app/src/main/assets/`.

### Подпись релиза

Создайте файл `android/keystore.properties` (он в `.gitignore`, в репозиторий не попадает):

```properties
storeFile=/полный/путь/kolobok-release.jks
storePassword=...
keyAlias=kolobok
keyPassword=...
```

Новый ключ создаётся так:

```bash
keytool -genkeypair -v -keystore kolobok-release.jks -alias kolobok -keyalg RSA -keysize 2048 -validity 10000
```

**Храните `.jks` и пароли в надёжном месте.** Все обновления приложения в RuStore
нужно подписывать тем же ключом, иначе новую версию загрузить не получится.

## Публикация в RuStore

1. Зарегистрируйтесь в консоли разработчика: https://console.rustore.ru
2. «Создать приложение» → загрузите `app-release.apk`.
   Имя пакета: `com.robutpit.kolobok`.
3. Иконка: `store/icon-512.png`. Скриншоты: `store/screenshot-*.png`.
4. Категория «Игры → Аркады», возрастной рейтинг 0+.
   Игра не собирает данные и не требует разрешений.
5. Для обновления увеличьте `versionCode` (и `versionName`) в `android/app/build.gradle`,
   соберите и подпишите тем же ключом.
