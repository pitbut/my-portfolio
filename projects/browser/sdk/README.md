# PitSDK — приложения и игры для PitBrowser

Приложение для PitBrowser — это обычный сайт (HTML, CSS, JavaScript, любые движки: Phaser, PixiJS,
Three.js, Godot/Unity WebGL…), упакованный в архив `.pitapp`. После установки он:

- появляется иконкой на главном экране PitBrowser (и, по желанию, ярлыком на рабочем столе телефона);
- запускается **на весь экран**, без адресной строки, в своей карточке «недавних приложений»;
- работает **без интернета** — все файлы лежат на телефоне;
- получает доступ к **датчикам, вибрации, рекордам** и т.д. через `pit.js`.

## Быстрый старт

```
my-game/
  manifest.json
  index.html
  icon.png        512×512, квадратная
  ...             любые файлы: js, картинки, звуки, wasm
```

**manifest.json**

```json
{
  "id": "my-game",
  "name": "Моя игра",
  "version": "1.0.0",
  "description": "Коротко об игре",
  "entry": "index.html",
  "icon": "icon.png",
  "orientation": "portrait",
  "permissions": ["sensors", "vibrate", "scores", "screen"],
  "scores": { "order": "desc", "unit": "очков" }
}
```

| Поле | Значение |
|---|---|
| `id` | латиница a-z, цифры и «-», 2–40 символов; уникален в магазине |
| `version` | при установке новой версии старая заменяется, рекорды сохраняются |
| `orientation` | `portrait`, `landscape` или `any` |
| `scores.order` | `desc` — больше лучше (очки), `asc` — меньше лучше (время) |
| `permissions` | см. ниже; без разрешения соответствующие функции не работают |

**index.html**

```html
<script src="pit.js"></script>
<script>
  pit.ready.then((info) => console.log('Запущено в', info.platform));
  pit.sensors.on('accelerometer', (e) => { const [x, y, z] = e.values; /* ... */ });
</script>
```

`pit.js` можно положить рядом (тогда игра работает и в обычном браузере), внутри PitBrowser
браузер всё равно подставит свою, актуальную версию.

**Упаковка:** заархивируйте **содержимое** папки (manifest.json должен быть в корне архива):

```bash
cd my-game && zip -r ../my-game.pitapp . && cd ..
```

**Установка:** откройте ссылку на `.pitapp` в PitBrowser (только `https://`) или
меню → «Установить приложение из файла». Браузер покажет название и разрешения и спросит согласие.

## Разрешения

| Разрешение | Что даёт | Спрашивается |
|---|---|---|
| `sensors` | `pit.sensors` — все датчики | при установке |
| `vibrate` | `pit.vibrate` | при установке |
| `scores` | `pit.scores`, `pit.player` | при установке |
| `screen` | `pit.screen` — не гаснуть, поворот | при установке |
| `headphones` | `pit.headphones` — наушники, кнопки гарнитуры | при установке |
| `buttons` | `pit.buttons` — кнопки громкости как игровые | при установке |
| `network` | доступ в интернет (без него — только свои файлы) | при установке |
| `camera` | `navigator.mediaDevices.getUserMedia({video})` | при установке **и** при первом использовании |
| `microphone` | `getUserMedia({audio})` | при установке **и** при первом использовании |
| `geolocation` | `navigator.geolocation` | при установке **и** при первом использовании |
| `bluetooth` | `pit.bluetooth` — BLE и Serial | при установке **и** при первом использовании |

Звук (Web Audio, `<audio>`), мультитач, геймпады (Gamepad API, в т.ч. Bluetooth-геймпады),
WebGL, WebAssembly, `localStorage`, IndexedDB работают без разрешений, как в обычном браузере.
У каждого приложения своё хранилище — другие приложения и сайты его не видят.

## API

Все методы возвращают `Promise`.

### Общее

```js
const info = await pit.ready;  // { id, name, version, native, platform, scoreOrder, scoreUnit, player, permissions }
pit.isNative                   // true — внутри PitBrowser, false — обычный браузер (режим отладки)
pit.on('pause', fn)            // приложение свернули — поставьте игру на паузу
pit.on('resume', fn)
pit.app.onBack(fn)             // своя обработка кнопки «Назад» (без неё «Назад» закрывает приложение)
pit.app.exit()                 // закрыть приложение
```

### Датчики

```js
const list = await pit.sensors.available();   // датчики именно этого телефона
const off = pit.sensors.on('accelerometer', (e) => {
  e.values      // [x, y, z]
  e.timestamp   // мс
  e.rotation    // поворот экрана: 0, 90, 180, 270
}, { hz: 60 });                               // частота 1–100 раз в секунду
off();                                        // отписаться
```

| Датчик | values | Единицы |
|---|---|---|
| `accelerometer` | x, y, z (с учётом силы тяжести) | м/с² |
| `linear_acceleration` | x, y, z (без силы тяжести — тряска, рывки) | м/с² |
| `gravity` | x, y, z | м/с² |
| `gyroscope` | скорость поворота вокруг x, y, z | рад/с |
| `magnetometer` | x, y, z | мкТл |
| `rotation_vector` | x, y, z, w (кватернион) | — |
| `orientation` | азимут (компас), наклон вперёд-назад, наклон вбок | градусы |
| `light` | освещённость | люкс |
| `proximity` | расстояние до объекта (часто 0 или максимум) | см |
| `pressure` | атмосферное давление | гПа |

Координаты — как у телефона в обычном положении: x вправо, y вверх по экрану, z из экрана.
Телефон лежит на столе: accelerometer ≈ [0, 0, 9.8]. Наклон правым краем вниз: x < 0.
Если игра в альбомной ориентации, пересчитайте оси по `e.rotation` (пример — в игре «Монетки»).

### Вибрация и экран

```js
pit.vibrate(40);                  // мс
pit.vibrate([100, 50, 100]);      // вибрация, пауза, вибрация...
pit.screen.keepOn(true);          // не гасить экран во время игры
pit.screen.orientation('landscape');
```

### Рекорды

```js
const r = await pit.scores.submit(1250);            // { best, rank, isRecord }
await pit.scores.submit(37.5, { level: '3' });      // отдельная таблица для уровня
const top = await pit.scores.top({ limit: 10 });    // [{ score, player, time, level }]
const best = await pit.scores.best();
const name = await pit.player.name();               // браузер спросит имя один раз
```

Рекорды хранит браузер (не сама игра), их видно в меню приложения на главном экране
(удерживайте иконку → «Рекорды»). Общие онлайн-таблицы лидеров появятся вместе с магазином.

### Bluetooth

Как в Chrome: приложение работает только с устройством, которое пользователь **сам выбрал** в окне
выбора. Выбор запоминается для этого приложения (`getDevices()`), другие приложения его не видят.
Если Bluetooth выключен, PitBrowser предложит включить его.

**BLE** — браслеты, пульсометры, датчики, ESP32/nRF, самодельные контроллеры:

```js
const dev = await pit.bluetooth.requestDevice({ services: ['heart_rate'] }); // окно выбора → { id, name }
const { services } = await pit.bluetooth.connect(dev);                       // список сервисов и характеристик

const battery = await pit.bluetooth.read(dev, 'battery_service', 'battery_level'); // Uint8Array
console.log(battery[0] + '%');

const unsubscribe = await pit.bluetooth.subscribe(dev, 'heart_rate', 'heart_rate_measurement', (e) => {
  console.log('пульс', e.value[1]);                                      // e.value — Uint8Array
});
await pit.bluetooth.write(dev, 'nordic_uart', 'nordic_uart_rx', 'LED ON\n'); // строка, массив байт, Uint8Array
pit.bluetooth.onDisconnect((e) => console.log('отключилось', e.device));
await pit.bluetooth.disconnect(dev);
```

- UUID можно писать полностью (`'6e400001-b5a3-…'`), коротко (`'180f'`, `0x180f`) или именем:
  `battery_service`, `battery_level`, `heart_rate`, `heart_rate_measurement`, `device_information`,
  `nordic_uart`, `nordic_uart_rx`, `nordic_uart_tx` и др.
- `requestDevice({ namePrefix: 'ESP32' })` — показать только устройства с таким началом имени.
- За одну запись — до 512 байт; длинные данные отправляйте частями.
- `pit.bluetooth.status()` → `{ supported, enabled, ble, classic }`.

**Serial** (классический Bluetooth SPP) — HC-05, HC-06, ESP32 `BluetoothSerial`. Устройство
нужно один раз сопрячь в настройках телефона:

```js
const dev = await pit.bluetooth.serial.requestDevice();   // выбор из сопряжённых
await pit.bluetooth.serial.connect(dev);
pit.bluetooth.serial.onData((e) => console.log(e.text));  // e.value — Uint8Array, e.text — строка
await pit.bluetooth.serial.write(dev, 'LED ON\n');
await pit.bluetooth.serial.disconnect(dev);
```

**Пример для ESP32:** [`examples/esp32-pit/esp32-pit.ino`](examples/esp32-pit/esp32-pit.ino) — BLE UART и
Serial одновременно, команды `LED ON` / `LED OFF` / `PING`, кнопка BOOT шлёт `BTN`. Проверить можно
встроенным приложением **«Bluetooth-терминал»**.

Bluetooth-геймпады подключаются в настройках телефона и работают через стандартный Gamepad API
(`navigator.getGamepads()`), без `pit.bluetooth`.

### Наушники и кнопки

```js
const s = await pit.headphones.state();
// { connected: true, devices: [{ type: 'bluetooth', name: 'Galaxy Buds', microphone: true }] }
// type: wired | bluetooth | usb | hearing_aid

pit.headphones.on((s) => console.log(s.change, s.devices));   // подключили / отключили
pit.headphones.onUnplug(() => game.muteMusic());               // выдернули — звук не должен заиграть из динамика

// Кнопки гарнитуры (проводной и Bluetooth): пока есть подписчики, они достаются игре, а не плееру
const off = pit.headphones.onButton((e) => {
  if (e.action === 'down' && e.button === 'play_pause') game.togglePause();
  // button: play_pause, play, pause, next, previous, stop, fast_forward, rewind
});
off(); // вернуть кнопки музыкальному плееру

// Кнопки громкости телефона как игровые (например, «огонь» и «прыжок»)
pit.buttons.onVolume((e) => { if (e.action === 'down') e.button === 'volume_up' ? jump() : fire(); });
```

Кнопки достаются игре, только пока она на экране; свернули — снова работают как обычно.
Объёмный звук в наушниках — стандартный Web Audio: `StereoPannerNode` или `PannerNode` (HRTF).
В обычном браузере `onButton`/`onVolume` реагируют на мультимедийные клавиши клавиатуры.

### Камера, микрофон, геолокация

Стандартные API браузера — PitBrowser сам спросит пользователя:

```js
const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' }, audio: true });
navigator.geolocation.watchPosition((p) => console.log(p.coords.latitude, p.coords.longitude));
// заранее спросить (например, на экране «Разрешите доступ к камере»):
await pit.permissions.request(['camera', 'microphone']);   // → { camera: true, microphone: false }
```

## Отладка на компьютере

Откройте `index.html` через любой локальный сервер (`npx serve my-game`) в Chrome. `pit.js`
работает в запасном режиме: рекорды — в `localStorage`, датчики — через стандартные события
браузера `devicemotion`/`deviceorientation` (на компьютере их обычно нет), разрешения всегда «да».
Поэтому добавьте в игру запасное управление с клавиатуры или мыши — так её удобно тестировать.
Окончательная проверка датчиков и вибрации — на телефоне в PitBrowser.

## Безопасность

- Возможности PitSDK доступны только установленным приложениям и только на их собственном адресе
  (`https://<id>.pitapp.robutpit.com`); обычные сайты в PitBrowser их не получают.
- Приложение не может запросить разрешение, которого нет в его `manifest.json`.
- Внешние ссылки открываются в обычной вкладке браузера, а не внутри приложения.
- Пакеты проверяются при установке: пути внутри архива, размер (до 200 МБ), наличие манифеста и файлов.

## Что дальше

- магазин приложений: публикация, проверка, обновления, онлайн-рекорды
- те же игры в PitBrowser на компьютере (с имитатором датчиков)
