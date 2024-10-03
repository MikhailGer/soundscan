#include <HX711_ADC.h>
#include <GyverStepper.h>
#include <ArduinoJson.h>

// Пины для компонентов
const int HX711_dout = 3;     // Пин для подключения HX711 (данные)
const int HX711_sck = 2;      // Пин для подключения HX711 (тактовый сигнал)
const int limitSwitchPin = 7; // Пин для концевика головки

// Объекты датчика и двигателей
HX711_ADC LoadCell(HX711_dout, HX711_sck);
GStepper<STEPPER2WIRE> stepper_base(200, 4, 5, 6);  // Мотор базы
GStepper<STEPPER2WIRE> stepper_head(200, 8, 9, 10); // Мотор головки

// Переменные состояния
bool Is_motor_on = false; // Управление двигателем базы
bool head_position = false; // false = поднята, true = опущена
int TenzoUpdateRate = 10;  // Частота обновления тензодатчика (мс)
int speed_base = 10;        // Текущая скорость базы
int pressure_threshold = 0; // Давление, требуемое для остановки головки
float currentTenzo = 0;    // Текущее значение тензодатчика

unsigned long lastUpdateTime = 0;

// JSON буфер и объект
const size_t capacity = JSON_OBJECT_SIZE(10);
StaticJsonDocument<capacity> jsonDoc;
char jsonBuffer[256];  // Буфер для хранения строкового JSON

// Прототипы функций
void handleIncomingData();
void parseJsonCommand(const char* json);
void executeCommand(const JsonDocument& doc);
void updateTenzoData();
void controlMotors();
void sendStatus();
void setupMotors();
void moveHeadUp();
void moveHeadDown();

void setup() {
  Serial.begin(115200);
  Serial.setTimeout(10);

  // Инициализация тензодатчика
  LoadCell.begin();
  LoadCell.start(2000, true);
  if (LoadCell.getTareTimeoutFlag()) {
    Serial.println("Ошибка: Проблема с тензодатчиком");
    while (1);
  } else {
    LoadCell.setCalFactor(491.25);
  }

  // Инициализация двигателей
  setupMotors();

  pinMode(limitSwitchPin, INPUT_PULLUP);  // Инициализация пина концевика
  head_position = !digitalRead(limitSwitchPin);  // Чтение начального состояния концевика

  Serial.println("Arduino готово к приему данных");
}

void loop() {
  handleIncomingData();  // Обработка входящих данных от компьютера
  updateTenzoData();     // Обновление данных с тензодатчика
  controlMotors();       // Управление двигателями на основе давления
  sendStatus();          // Отправка статуса обратно на компьютер
}

// Обработка входящих данных и вызов обработчика JSON
void handleIncomingData() {
  if (Serial.available() > 0) {
    size_t len = Serial.readBytesUntil('\n', jsonBuffer, sizeof(jsonBuffer) - 1);
    jsonBuffer[len] = '\0';  // Завершаем строку
    parseJsonCommand(jsonBuffer);
  }
}

// Парсинг JSON-строки и выполнение команды
void parseJsonCommand(const char* json) {
  DeserializationError error = deserializeJson(jsonDoc, json);
  if (error) {
    Serial.println("Ошибка парсинга JSON");
    return;
  }
  executeCommand(jsonDoc);  // Выполняем команду
}

// Обработка и выполнение команды на основе содержимого JSON
void executeCommand(const JsonDocument& doc) {
  const char* command = doc["command"];  // Команда из JSON
  if (strcmp(command, "connect") == 0) {
    Serial.println("connected");
  } else if (strcmp(command, "set_tenzo_rate") == 0) {
    TenzoUpdateRate = doc["rate"];
  } else if (strcmp(command, "set_base_speed") == 0) {
    speed_base = doc["speed"];
    stepper_base.setSpeed(speed_base);  // Устанавливаем скорость
  } else if (strcmp(command, "set_motor_on") == 0) {
    Is_motor_on = doc["state"];
    if (Is_motor_on) {
      stepper_base.enable();  // Включить мотор базы
    } else {
      stepper_base.disable();  // Отключить мотор базы
    }
  } else if (strcmp(command, "move_head_up") == 0) {
    moveHeadUp();  // Поднять головку
  } else if (strcmp(command, "move_head_down") == 0) {
    pressure_threshold = doc["pressure"];  // Установить давление для остановки
    moveHeadDown();  // Опустить головку
  }
}

// Обновление данных с тензодатчика
void updateTenzoData() {
  if (millis() - lastUpdateTime >= TenzoUpdateRate) {
    lastUpdateTime = millis();
    if (LoadCell.update()) {
      currentTenzo = LoadCell.getData();  // Получение данных с тензодатчика
    }
  }
}

// Управление головкой на основе давления
void controlMotors() {
  if (head_position && currentTenzo >= pressure_threshold) {
    moveHeadUp();  // Автоматически поднимаем головку, если давление превышено
  }
}

// Функция для подъема головки
void moveHeadUp() {
  stepper_head.setSpeed(300);     // Скорость подъема головки
  stepper_head.setMaxSpeed(300);  // Максимальная скорость подъема
  stepper_head.setTarget(-10000, RELATIVE);  // Подняться вверх
  while (digitalRead(limitSwitchPin) == HIGH) {
    stepper_head.tick();  // Выполняем движение до разжатия концевика
  }
  head_position = false;  // Обновляем состояние головки
}

// Функция для опускания головки
void moveHeadDown() {
  stepper_head.setSpeed(300);     // Скорость опускания головки
  stepper_head.setMaxSpeed(300);  // Максимальная скорость опускания
  stepper_head.setTarget(10000, RELATIVE);  // Опуститься вниз
  while (digitalRead(limitSwitchPin) == LOW) {
    stepper_head.tick();  // Выполняем движение до замыкания концевика
  }
  head_position = true;  // Обновляем состояние головки
}

// Отправка статуса в JSON формате
void sendStatus() {
  jsonDoc.clear();
  jsonDoc["current_weight"] = currentTenzo;
  jsonDoc["base_motor_on"] = Is_motor_on;
  jsonDoc["head_position"] = head_position ? "down" : "up";
  serializeJson(jsonDoc, Serial);  // Отправка JSON данных
  Serial.println();  // Завершающий символ строки
}

// Установка начальных параметров двигателей
void setupMotors() {
  stepper_base.disable();
  stepper_head.disable();
  stepper_base.setRunMode(FOLLOW_POS);
  stepper_head.setRunMode(FOLLOW_POS);
}
