#include <Arduino.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>
#include <BLEAdvertising.h>

// Testing 1 ESP32-C3 BLE stirrer firmware.
// Board: ESP32-C3
// Motor: NEMA 17 through A4988

static const char *DEVICE_NAME = "KitchenStirrer";
static const char *SERVICE_UUID = "8a4f1000-0b38-4f4d-8b5f-6e5d7f0c1000";
static const char *RX_UUID = "8a4f1001-0b38-4f4d-8b5f-6e5d7f0c1000";
static const char *TX_UUID = "8a4f1002-0b38-4f4d-8b5f-6e5d7f0c1000";

static const int STEP_PIN = 4;
static const int DIR_PIN = 5;
static const int ENABLE_PIN = 6;

BLECharacteristic *txCharacteristic;

volatile bool motorEnabled = false;
volatile bool directionClockwise = true;
volatile uint32_t stepDelayMicros = 2500;
uint32_t lastStepMicros = 0;

void sendStatus(const String &message) {
  Serial.println(message);
  if (txCharacteristic != nullptr) {
    txCharacteristic->setValue(message.c_str());
    txCharacteristic->notify();
  }
}

void stopMotor() {
  motorEnabled = false;
  digitalWrite(ENABLE_PIN, HIGH);
  sendStatus("OK STOP");
}

void startMotor(uint32_t delayMicros, bool clockwise) {
  stepDelayMicros = delayMicros;
  directionClockwise = clockwise;
  digitalWrite(DIR_PIN, directionClockwise ? HIGH : LOW);
  digitalWrite(ENABLE_PIN, LOW);
  motorEnabled = true;
  sendStatus("OK START");
}

uint32_t profileDelay(const String &profile) {
  if (profile == "slow") return 5000;
  if (profile == "medium") return 2500;
  if (profile == "fast") return 1200;
  return 5000;
}

void handleCommand(String command) {
  command.trim();
  command.toLowerCase();

  if (command == "stop" || command == "emergency_stop") {
    stopMotor();
    return;
  }

  if (command.startsWith("start_profile ")) {
    String profile = command.substring(String("start_profile ").length());
    startMotor(profileDelay(profile), true);
    return;
  }

  if (command.startsWith("start ")) {
    uint32_t delayMicros = command.substring(String("start ").length()).toInt();
    if (delayMicros < 800) {
      sendStatus("ERR DELAY_TOO_LOW");
      return;
    }
    startMotor(delayMicros, true);
    return;
  }

  if (command == "reverse") {
    directionClockwise = !directionClockwise;
    digitalWrite(DIR_PIN, directionClockwise ? HIGH : LOW);
    sendStatus("OK REVERSE");
    return;
  }

  if (command == "status") {
    sendStatus(motorEnabled ? "STATUS RUNNING" : "STATUS STOPPED");
    return;
  }

  sendStatus("ERR UNKNOWN_COMMAND");
}

class RxCallbacks : public BLECharacteristicCallbacks {
  void onWrite(BLECharacteristic *characteristic) override {
    String value = characteristic->getValue().c_str();
    handleCommand(value);
  }
};

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("KitchenStirrer booting");

  pinMode(STEP_PIN, OUTPUT);
  pinMode(DIR_PIN, OUTPUT);
  pinMode(ENABLE_PIN, OUTPUT);
  digitalWrite(ENABLE_PIN, HIGH);

  BLEDevice::init(DEVICE_NAME);
  BLEServer *server = BLEDevice::createServer();
  BLEService *service = server->createService(SERVICE_UUID);

  BLECharacteristic *rxCharacteristic = service->createCharacteristic(
    RX_UUID,
    BLECharacteristic::PROPERTY_WRITE | BLECharacteristic::PROPERTY_WRITE_NR
  );
  rxCharacteristic->setCallbacks(new RxCallbacks());

  txCharacteristic = service->createCharacteristic(
    TX_UUID,
    BLECharacteristic::PROPERTY_NOTIFY
  );
  txCharacteristic->addDescriptor(new BLE2902());

  service->start();
  BLEAdvertising *advertising = BLEDevice::getAdvertising();

  BLEAdvertisementData advertisementData;
  advertisementData.setName(DEVICE_NAME);
  advertisementData.setCompleteServices(BLEUUID(SERVICE_UUID));
  advertising->setAdvertisementData(advertisementData);

  BLEAdvertisementData scanResponseData;
  scanResponseData.setName(DEVICE_NAME);
  advertising->setScanResponseData(scanResponseData);

  advertising->addServiceUUID(SERVICE_UUID);
  advertising->setName(DEVICE_NAME);
  advertising->setScanResponse(true);
  advertising->start();
  Serial.println("KitchenStirrer BLE advertising started");
  Serial.println("Device name: KitchenStirrer");
}

void loop() {
  if (!motorEnabled) {
    delay(10);
    return;
  }

  uint32_t now = micros();
  if (now - lastStepMicros >= stepDelayMicros) {
    lastStepMicros = now;
    digitalWrite(STEP_PIN, HIGH);
    delayMicroseconds(3);
    digitalWrite(STEP_PIN, LOW);
  }
}
