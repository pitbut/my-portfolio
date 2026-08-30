# Тараканьи бега — Android

Нативное Android-приложение (Kotlin + Jetpack Compose): порода/окрас таракана,
кормёжка и тренировка, выбор трассы, «живой» нелинейный бег, реакция на
громкий звук (микрофон) и удар по столу (акселерометр), гонка по Bluetooth
(классический RFCOMM) вдвоём на одном общем поле.

Готовый APK для установки: [`dist/roach-race-debug.apk`](dist/roach-race-debug.apk)
(debug-подпись, ставится как обычный APK).

## Сборка из исходников

Нужны JDK 17+ и Android SDK (platform 34, build-tools 34.0.0).

```bash
echo "sdk.dir=/путь/к/Android/Sdk" > local.properties
./gradlew assembleDebug
```

APK появится в `app/build/outputs/apk/debug/app-debug.apk`.

## Известные ограничения

- Bluetooth-режим написан по стандартному Android RFCOMM API и собирается
  без ошибок, но не тестировался на паре живых телефонов.
- Режим «сложить телефоны в одно большое поле» (у каждого свой участок
  трассы) не реализован — только общее поле, зеркалируемое на оба экрана.
- Рассчитан на 2 игроков по Bluetooth; N-игроков и публикация в
  RuStore/Google Play — следующие шаги.
