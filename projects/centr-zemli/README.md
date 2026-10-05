# Путешествие к центру Земли

Аркада по мотивам романа Жюля Верна. Одна кодовая база: веб-игра (`index.html`, `game.js`, `style.css`)
и Android-приложение (`android/`), которое при сборке копирует эти файлы в `assets/www` и показывает их в WebView.

## Главы

1. **Кратер Снайфедльса.** Спуск по базальтовому жерлу, камнепады, сталактиты, темнота.
2. **Галереи. Жажда.** Вода быстро убывает, пить можно из струй Гансбаха.
3. **Море Лиденброка.** Плот, ихтиозавр, плезиозавр, шаровая молния.
4. **Подземный лес.** Гигантские грибы, мастодонты, силуэт пастуха-великана.
5. **Извержение.** Подъём вверх по жерлу и лавовые бомбы. Финал — остров Стромболи.

В каждой главе спрятана руна Сакнуссема. Прогресс, рекорд и руны сохраняются в `localStorage`.

## Сборка APK

Нужны JDK 17+ и Android SDK (platform 35).

```bash
cd android
echo "sdk.dir=/путь/к/android-sdk" > local.properties
# keystore.properties рядом с .jks (оба файла в git не попадают):
#   storeFile=centrzemli-release.jks
#   storePassword=...
#   keyAlias=centrzemli
#   keyPassword=...
./gradlew assembleRelease
# результат: app/build/outputs/apk/release/app-release.apk
```

Без `keystore.properties` получится неподписанный релиз. RuStore примет только APK, подписанный тем же
ключом, что и первая версия, поэтому храните `.jks` и пароль в надёжном месте.

Для обновления в RuStore увеличьте `versionCode` (и `versionName`) в `android/app/build.gradle`.

Собранный APK версии 1.0: [`centr-zemli-1.0.apk`](centr-zemli-1.0.apk).
Пакет: `com.robutpit.centrzemli`, minSdk 24 (Android 7.0), targetSdk 35. Разрешения: только `VIBRATE`.
