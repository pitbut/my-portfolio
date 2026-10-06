/*
 * ESP32 ↔ PitBrowser: управление по Bluetooth из игры/приложения.
 *
 * Работает сразу двумя способами:
 *   - BLE UART (Nordic UART Service) — pit.bluetooth.requestDevice({ services: ['nordic_uart'] })
 *   - классический Bluetooth Serial (SPP) — pit.bluetooth.serial.requestDevice()
 *     (только ESP32 «классический»; у ESP32-S3/C3 классического Bluetooth нет — используйте BLE)
 *
 * Команды (строка + \n): LED ON, LED OFF, PING. Кнопка на GPIO0 (BOOT) отправляет «BTN».
 * Плата: ESP32 Dev Module, Arduino-ESP32 2.x или 3.x.
 */
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLE2902.h>
#if defined(CONFIG_BT_CLASSIC_ENABLED)
#include <BluetoothSerial.h>
BluetoothSerial SerialBT;
#endif

#define NUS_SERVICE "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
#define NUS_RX      "6e400002-b5a3-f393-e0a9-e50e24dcca9e"  // телефон → ESP32
#define NUS_TX      "6e400003-b5a3-f393-e0a9-e50e24dcca9e"  // ESP32 → телефон (уведомления)

const int LED_PIN = 2;
const int BTN_PIN = 0;

BLECharacteristic *txChar;
bool bleConnected = false;
String bleLine;

void sendLine(const String &s) {
  String line = s + "\n";
  if (bleConnected) {
    txChar->setValue((uint8_t *)line.c_str(), line.length());
    txChar->notify();
  }
#if defined(CONFIG_BT_CLASSIC_ENABLED)
  if (SerialBT.hasClient()) SerialBT.print(line);
#endif
  Serial.print("→ " + line);
}

void handleCommand(String cmd) {
  cmd.trim();
  if (cmd.isEmpty()) return;
  Serial.println("← " + cmd);
  if (cmd == "LED ON") { digitalWrite(LED_PIN, HIGH); sendLine("OK LED ON"); }
  else if (cmd == "LED OFF") { digitalWrite(LED_PIN, LOW); sendLine("OK LED OFF"); }
  else if (cmd == "PING") sendLine("PONG " + String(millis()));
  else sendLine("? " + cmd);
}

class ServerCallbacks : public BLEServerCallbacks {
  void onConnect(BLEServer *) override { bleConnected = true; }
  void onDisconnect(BLEServer *server) override {
    bleConnected = false;
    server->getAdvertising()->start();  // снова видно для поиска
  }
};

class RxCallbacks : public BLECharacteristicCallbacks {
  void onWrite(BLECharacteristic *c) override {
    auto v = c->getValue();  // std::string (2.x) или String (3.x) — оба подходят
    for (size_t i = 0; i < v.length(); i++) {
      char ch = v[i];
      if (ch == '\n') { handleCommand(bleLine); bleLine = ""; }
      else if (ch != '\r') bleLine += ch;
    }
  }
};

void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  pinMode(BTN_PIN, INPUT_PULLUP);

  BLEDevice::init("ESP32-Pit");
  BLEServer *server = BLEDevice::createServer();
  server->setCallbacks(new ServerCallbacks());
  BLEService *service = server->createService(NUS_SERVICE);
  txChar = service->createCharacteristic(NUS_TX, BLECharacteristic::PROPERTY_NOTIFY);
  txChar->addDescriptor(new BLE2902());
  BLECharacteristic *rx = service->createCharacteristic(NUS_RX, BLECharacteristic::PROPERTY_WRITE | BLECharacteristic::PROPERTY_WRITE_NR);
  rx->setCallbacks(new RxCallbacks());
  service->start();
  BLEAdvertising *adv = BLEDevice::getAdvertising();
  adv->addServiceUUID(NUS_SERVICE);
  adv->setScanResponse(true);
  BLEDevice::startAdvertising();

#if defined(CONFIG_BT_CLASSIC_ENABLED)
  SerialBT.begin("ESP32-Pit-Serial");  // сопрягите в настройках телефона
#endif
  Serial.println("Готово: ищите ESP32-Pit в Bluetooth-терминале PitBrowser");
}

void loop() {
#if defined(CONFIG_BT_CLASSIC_ENABLED)
  static String btLine;
  while (SerialBT.available()) {
    char ch = SerialBT.read();
    if (ch == '\n') { handleCommand(btLine); btLine = ""; }
    else if (ch != '\r') btLine += ch;
  }
#endif
  static bool lastBtn = HIGH;
  bool btn = digitalRead(BTN_PIN);
  if (btn == LOW && lastBtn == HIGH) sendLine("BTN");
  lastBtn = btn;
  delay(10);
}
