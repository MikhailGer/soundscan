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

//переменные, связанные с постоянными параметрами установки
static int pressure_to_find_blade = 5; //постоянное значение, если показания тензодатчика больше этого значения, значит тезодатчик уперся в лопатку(лопатка найдена)
static int circle_in_steps = 14400; //полная окружность установки в шагах
static int serach_interval = 7000; //интревал времени в мc. Если в течении этого времени новая лопатка не была найдена, сканирование завершается(возоврат к старту)
int32_t base_init_pos = 0; //задает стартовую позицию, присвоение происходит в setupMotors()

// Переменные состояния 
bool blade_found = false; //переменная состояние поиска лопатки
bool Is_motor_on = false; // Управление двигателем базы
bool head_position = false; // false = поднята, true = опущена
int TenzoUpdateRate = 10;  // Частота обновления тензодатчика (мс)
int pressure_threshold = 0; // Давление, требуемое для остановки головки
float currentTenzo = 0;    // Текущее значение тензодатчика
unsigned long lastUpdateTime = 0;

int speed_base = 10;        // Текущая скорость базы(в целом не нужно, можно оперировать maxspeed и acceleration)
int accel_base = 0;//ускорение базы
int MaxSpeed_base = 0; //макс скорость базы

int speed_head = 0; //текущая скорость медиатора(в целом не нужно, можно оперировать maxspeed и acceleration)
int accel_head = 0;//ускорение медиатора
int MaxSpeed_head = 0; //макс скорость медиатора

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
void moveHeadUp(int start_speed,int accel, int MaxSpeed);
void moveHeadDown(int start_speed,int accel, int MaxSpeed);
void find_blade();
void ding();
void return_base();

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
//  controlMotors();       // Управление двигателями на основе давления
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
    TenzoUpdateRate = doc["rate"].as<int>();
  } else if (strcmp(command, "set_base_settings") == 0) {
    
    if (doc.containsKey("speed")){
      speed_base = doc["speed"].as<int>();
      }
    if (doc.containsKey("accel")){
      accel_base = doc["accel"].as<int>();
      }
    if (doc.containsKey("MaxSpeed")){
      MaxSpeed_base = doc["MaxSpeed"].as<int>();
      }
//    stepper_base.setSpeed(speed_base);  // Устанавливаем скорость
  } 
  else if (strcmp(command, "set_head_settings") == 0) {
    
    if (doc.containsKey("speed")){
      speed_head = doc["speed"].as<int>();
      }
    if (doc.containsKey("accel")){
      accel_head = doc["accel"].as<int>();
      }
    if (doc.containsKey("MaxSpeed")){
      MaxSpeed_head = doc["MaxSpeed"].as<int>();
      }
  }
  else if (strcmp(command, "set_motor_on") == 0) {
      Is_motor_on = doc["state"].as<bool>();
      if (Is_motor_on) {
          stepper_base.enable();  // Включить мотор базы
      } else {
          stepper_base.disable();  // Отключить мотор базы
      }
  } else if (strcmp(command, "move_head_up") == 0) {
      moveHeadUp(speed_head,accel_head,MaxSpeed_head);  // Поднять головку
  } else if (strcmp(command, "move_head_down") == 0) {
      pressure_threshold = doc["pressure"].as<int>();  // Установить давление для остановки
      moveHeadDown(speed_head,accel_head,MaxSpeed_head);  // Опустить головку
  }
     else if (strcmp(command, "find_blade") == 0){
      find_blade();
      }
    else if (strcmp(command, "return_base") == 0){
      return_base();
      }
    else if (strcmp(command, "ding") == 0){
      ding();
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


//void controlMotors() {
//  if (head_position && (currentTenzo >= pressure_threshold)) {
//    moveHeadUp(speed_head,accel_head,MaxSpeed_head);  // Автоматически поднимаем головку, если давление превышено
//  }
//}

// Функция для подъема головки
void moveHeadUp(int start_speed,int accel, int MaxSpeed) {
  stepper_head.setSpeed(start_speed);     // Скорость подъема головки
  stepper_head.setAcceleration(accel); 
  stepper_head.setMaxSpeed(MaxSpeed);  // Максимальная скорость подъема
  stepper_head.setTarget(-10000, RELATIVE);  // Подняться вверх
  while (digitalRead(limitSwitchPin) == HIGH) {
    stepper_head.tick();  // Выполняем движение до разжатия концевика
  }
  head_position = false;  // Обновляем состояние головки
}

// Функция для опускания головки
void moveHeadDown(int start_speed,int accel, int MaxSpeed) {
  stepper_head.setSpeed(start_speed);     // Скорость опускания головки
  stepper_head.setAcceleration(accel); 
  stepper_head.setMaxSpeed(MaxSpeed);  // Максимальная скорость опускания
  stepper_head.setTarget(10000, RELATIVE);  // Опуститься вниз
  while (digitalRead(limitSwitchPin) == LOW) {
    stepper_head.tick();  // Выполняем движение до замыкания концевика
  }
  head_position = true;  // Обновляем состояние головки
}


void find_blade(){
  if(blade_found == false && head_position == true){
    unsigned long start_scan_time = millis();
    unsigned long current_scan_time = 0;
    stepper_base.setTarget(circle_in_steps, ABSOLUTE);//отпраляем базу вращаться
    while(stepper_base.tick() == true &&(current_scan_time - start_scan_time <= serach_interval)){
        current_scan_time = millis();
        updateTenzoData();
        if (blade_found == false &&(currentTenzo >= pressure_to_find_blade)){
          blade_found = true;
          ding();
          stepper_base.brake();
          jsonDoc.clear();
          jsonDoc["is_blade_found"] = blade_found;
          serializeJson(jsonDoc, Serial);  // Отправка JSON данных
          Serial.println(); 
          }
         }
    
    return_base();

  }
  }

void ding(){
  if(blade_found == true && head_position == true){
    updateTenzoData();
    while(currentTenzo < pressure_threshold){
      stepper_base.tick();
      }
      stepper_base.brake();
      moveHeadUp(speed_head,accel_head,MaxSpeed_head);  // Автоматически поднимаем головку, если давление превышено
      blade_found == false;
  }
  }
// Отправка статуса в JSON формате
void return_base(){
  if (head_position == true){
      moveHeadUp(speed_head, accel_head,MaxSpeed_head);
      }
    stepper_base.setSpeed(0);     //выставляем макс скорость для быстрого возврата
    stepper_base.setAcceleration(2000); //выставляем макс скорость для быстрого возврата
    stepper_base.setMaxSpeed(8000);//выставляем макс скорость для быстрого возврата
    
    stepper_base.setTarget(base_init_pos, ABSOLUTE); //задаем стартовую позицию
    
    while(stepper_base.tick() == true){ //ждем пока база вернется к старту
      continue;
      }
      
     //выставляем обратно заданные настройками значения
    stepper_base.setSpeed(speed_base);
    stepper_base.setAcceleration(accel_base); 
    stepper_base.setMaxSpeed(MaxSpeed_base);
  
  }
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
  stepper_base.enable();//включаем двигатели
  stepper_head.enable();//включаем двигатели
  stepper_base.setRunMode(FOLLOW_POS);
  stepper_head.setRunMode(FOLLOW_POS);
  base_init_pos = stepper_head.getCurrent();
  
}
