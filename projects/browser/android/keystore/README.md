# Ключи подписи

## Ключ для публикации (IlovaBozor, RuStore)

Хранится **только у владельца**, в git его нет. Сборка подписывается им, если есть:
- файл `android/keystore.properties` (в `.gitignore`):
  ```
  storeFile=/путь/к/pitbrowser-release.jks
  storePassword=…
  keyAlias=pitbrowser
  keyPassword=…
  ```
- или переменные окружения `PIT_KEYSTORE`, `PIT_KEYSTORE_PASSWORD`, `PIT_KEY_ALIAS`, `PIT_KEY_PASSWORD`;
  в GitHub Actions — секреты `PIT_KEYSTORE_BASE64` (файл ключа в base64), `PIT_KEYSTORE_PASSWORD`,
  `PIT_KEY_ALIAS`, `PIT_KEY_PASSWORD`.

SHA-256 сертификата: `F6:61:B3:73:66:6B:8C:08:2D:B7:60:4B:1B:6C:67:9A:72:0D:BC:B9:F6:EF:01:60:18:04:E1:1A:DD:0F:58:D3`

Все версии в магазинах должны подписываться этим ключом — иначе обновление у пользователей не встанет.

## Тестовый ключ

`pitbrowser-test.keystore` — **открытый тестовый ключ** (пароль `android`, alias `androiddebugkey`)
для отладочных сборок и сборок без ключа для публикации. Не годится для магазинов.
Приложения, подписанные тестовым и настоящим ключом, — для Android разные: чтобы перейти с одного на
другой, приложение нужно один раз удалить.
