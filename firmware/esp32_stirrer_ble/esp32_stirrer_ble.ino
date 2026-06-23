#include <Arduino.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>
#include <BLEAdvertising.h>

// Testing 1 ESP32-C3 BLE stirrer firmware.
// Board: ESP32-C3
// Motor: NEMA 17 through A4988
// Servos: 2x SG90, controlled one at a time.

static const char *DEVICE_NAME = "KitchenStirrer";
static const char *SERVICE_UUID = "8a4f1000-0b38-4f4d-8b5f-6e5d7f0c1000";
static const char *RX_UUID = "8a4f1001-0b38-4f4d-8b5f-6e5d7f0c1000";
static const char *TX_UUID = "8a4f1002-0b38-4f4d-8b5f-6e5d7f0c1000";

static const int STEP_PIN = 4;
static const int DIR_PIN = 5;
static const int ENABLE_PIN = 6;
static const int LIFT_SERVO_PIN = 7;
static const int REACH_SERVO_PIN = 10;

static const uint32_t SERVO_FREQ_HZ = 50;
static const uint8_t SERVO_PWM_BITS = 14;
static const uint32_t SERVO_PWM_MAX = (1UL << SERVO_PWM_BITS) - 1;
static const uint16_t SERVO_MIN_US = 500;
static const uint16_t SERVO_MAX_US = 2400;
static const uint16_t SERVO_SETTLE_MS = 450;

static const int LIFT_DOWN_ANGLE = 35;
static const int LIFT_UP_ANGLE = 115;
static const int REACH_BACK_ANGLE = 35;
static const int REACH_CENTER_ANGLE = 85;
static const int REACH_FRONT_ANGLE = 135;

BLECharacteristic *txCharacteristic;
String serialCommandBuffer = "";

volatile bool motorEnabled = false;
volatile bool directionClockwise = true;
volatile uint32_t stepDelayMicros = 2500;
uint32_t lastStepMicros = 0;
int liftServoAngle = LIFT_UP_ANGLE;
int reachServoAngle = REACH_CENTER_ANGLE;

void sendStatus(const String &message) {
  Serial.println(message);
  if (txCharacteristic != nullptr) {
    txCharacteristic->setValue(message.c_str());
    txCharacteristic->notify();
  }
}

void stopMotor(bool report = true) {
  motorEnabled = false;
  digitalWrite(ENABLE_PIN, HIGH);
  if (report) {
    sendStatus("OK STOP");
  }
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

uint32_t servoDutyFromMicros(uint16_t pulseMicros) {
  return static_cast<uint32_t>((static_cast<uint64_t>(pulseMicros) * SERVO_PWM_MAX) / 20000ULL);
}

void writeServoAngle(int pin, int angle) {
  int safeAngle = constrain(angle, 0, 180);
  uint16_t pulseMicros = map(safeAngle, 0, 180, SERVO_MIN_US, SERVO_MAX_US);
  ledcWrite(pin, servoDutyFromMicros(pulseMicros));
}

void setupServos() {
  ledcAttach(LIFT_SERVO_PIN, SERVO_FREQ_HZ, SERVO_PWM_BITS);
  ledcAttach(REACH_SERVO_PIN, SERVO_FREQ_HZ, SERVO_PWM_BITS);
  writeServoAngle(LIFT_SERVO_PIN, liftServoAngle);
  writeServoAngle(REACH_SERVO_PIN, reachServoAngle);
}

bool moveServoOnly(const String &servoName, int angle, bool report = true) {
  stopMotor(false);

  if (servoName == "lift") {
    liftServoAngle = constrain(angle, 0, 180);
    writeServoAngle(LIFT_SERVO_PIN, liftServoAngle);
    delay(SERVO_SETTLE_MS);
    if (report) {
      sendStatus("OK SERVO lift " + String(liftServoAngle));
    }
    return true;
  }

  if (servoName == "reach") {
    reachServoAngle = constrain(angle, 0, 180);
    writeServoAngle(REACH_SERVO_PIN, reachServoAngle);
    delay(SERVO_SETTLE_MS);
    if (report) {
      sendStatus("OK SERVO reach " + String(reachServoAngle));
    }
    return true;
  }

  sendStatus("ERR UNKNOWN_SERVO");
  return false;
}

void handleServoCommand(String command) {
  command.trim();

  if (command == "servo home") {
    moveServoOnly("lift", LIFT_UP_ANGLE, false);
    moveServoOnly("reach", REACH_CENTER_ANGLE, false);
    sendStatus("OK SERVO home");
    return;
  }

  if (!command.startsWith("servo ")) {
    sendStatus("ERR SERVO_COMMAND");
    return;
  }

  String rest = command.substring(String("servo ").length());
  int separator = rest.indexOf(' ');
  if (separator < 0) {
    sendStatus("ERR SERVO_TARGET");
    return;
  }

  String servoName = rest.substring(0, separator);
  String position = rest.substring(separator + 1);
  int angle = -1;

  if (servoName == "lift") {
    if (position == "up") angle = LIFT_UP_ANGLE;
    if (position == "down") angle = LIFT_DOWN_ANGLE;
  }

  if (servoName == "reach") {
    if (position == "back") angle = REACH_BACK_ANGLE;
    if (position == "center") angle = REACH_CENTER_ANGLE;
    if (position == "front") angle = REACH_FRONT_ANGLE;
  }

  if (position.startsWith("angle:")) {
    angle = position.substring(String("angle:").length()).toInt();
  }

  if (angle < 0 || angle > 180) {
    sendStatus("ERR SERVO_POSITION");
    return;
  }

  moveServoOnly(servoName, angle);
}

void handleCommand(String command) {
  command.trim();
  command.toLowerCase();

  if (command == "stop" || command == "emergency_stop") {
    stopMotor();
    return;
  }

  if (command.startsWith("servo ")) {
    handleServoCommand(command);
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
    sendStatus(
      String(motorEnabled ? "STATUS RUNNING" : "STATUS STOPPED")
      + " lift=" + String(liftServoAngle)
      + " reach=" + String(reachServoAngle)
    );
    return;
  }

  sendStatus("ERR UNKNOWN_COMMAND");
}

void readSerialCommands() {
  while (Serial.available() > 0) {
    char incoming = static_cast<char>(Serial.read());
    if (incoming == '\n' || incoming == '\r') {
      if (serialCommandBuffer.length() > 0) {
        handleCommand(serialCommandBuffer);
        serialCommandBuffer = "";
      }
      continue;
    }

    if (serialCommandBuffer.length() < 120) {
      serialCommandBuffer += incoming;
    } else {
      serialCommandBuffer = "";
      sendStatus("ERR COMMAND_TOO_LONG");
    }
  }
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
  setupServos();

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
  readSerialCommands();

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
