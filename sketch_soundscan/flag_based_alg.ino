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
static int prepearing_time = 5000; // время в мс, которое требуется микрофону для записи колебаний звука после "дзынь", после этого времени начнется поиск новой лопатки
static int pressure_to_find_blade = 20; //постоянное значение, если показания тензодатчика больше этого значения, значит тезодатчик уперся в лопатку(лопатка найдена)
static int circle_in_steps = 14400; //полная окружность установки в шагах
static int serach_interval = 7000; //интревал времени в мc. Если в течении этого времени новая лопатка не была найдена, сканирование завершается(возоврат к старту)
int32_t base_init_pos = 0; //задает стартовую позицию, присвоение происходит в setupMotors()

// Переменные состояния 
unsigned long find_blade_start_time = 0;
unsigned long wait_recording_start_time = 0;
bool blade_found = false; //переменная состояние поиска лопатки
bool Is_motor_on = false; // Управление двигателем базы
bool head_position = false; // false = поднята, true = опущена
int TenzoUpdateRate = 10;  // Частота обновления тензодатчика (мс)
int StatusUpdateRate = 10; //Частота обновления статуса 
int pressure_threshold = 0; // Давление, требуемое для остановки головки
float currentTenzo = 0;    // Текущее значение тензодатчика
unsigned long lastUpdateTime = 0;
unsigned long LastStatusUpdate = 0;

//bool status_flag = false; //если true - выводить данные (логика вывода статуса изменена)

//флаги режимов
bool find_blade_in_progress = false;
bool head_lifting = false;
bool head_falling = false;
bool pressure_reached = false;
bool pulling_blade = false;
bool making_ding = false;
bool prepearing_for_new_blade = false;
bool base_returning = false;
bool base_run_flag = false;

//!!!!!!!!!!!!!!!!!
int blade_width = 100;//расстояние в шагах двигателя которое требуется для того чтобы переступить через шину лопатку(для того чтобы после дзыня головка опускалась не на лопатку а готовилась к новой лопатке)

int speed_base = 0;        // Текущая скорость базы(в целом не нужно, можно оперировать maxspeed и acceleration)
int accel_base = 0;//ускорение базы
int MaxSpeed_base = 0; //макс скорость базы

int speed_head = 1000; //текущая скорость медиатора(в целом не нужно, можно оперировать maxspeed и acceleration)
int accel_head = 2000;//ускорение медиатора
int MaxSpeed_head = 1000; //макс скорость медиатора

// JSON буфер и объект
const size_t capacity = 400;
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
  stepper_head.reset();
}

void loop() {
  handleIncomingData();  // Обработка входящих данных от компьютера      
  updateTenzoData();

  if (find_blade_in_progress) {
    
    if (base_run_flag){ // флаг разрешения движения двигателя базы
      if (!stepper_base.tick()){
          if (!head_lifting && head_position){ //логика "заряжания" медиатора на поднятие
        head_lifting = true;
        stepper_head.reset();
        stepper_head.setSpeed(3000);     // задаем макс скорость для издавания звука
        stepper_head.setAcceleration(2000); 
        stepper_head.setMaxSpeed(8000);  // Максимальная скорость подъема
        stepper_head.setTarget(3200, RELATIVE);
      }
        
        
       if (head_lifting){ //логика поднятия медиатора
            head_falling = false;
            if(!stepper_head.tick()){ //за счет stepper_head.tick() происходит движение до ранее заданного значения которое находится в парсере комманд
            head_lifting = false;
            head_position = false; // Обновляем положение головки(головка опускается - выходит на нерабочее положение, поэтому head_position = false)
            pressure_reached = false;
            pulling_blade = false;
            making_ding = false;
            wait_recording_start_time = 0;
            prepearing_for_new_blade = false; // обнуление всех флагов
            find_blade_in_progress = false;
            base_run_flag = false;
            blade_found = false;
            return_base();
          }
        }
  
          
        }
      }
      
    if (!blade_found){ // условие для того, чтобы в случае нахождения лопатки база остановилась до команды "pull_blade"
//    stepper_base.tick();
    base_run_flag = true;
    updateTenzoData();
    }   else{
            find_blade_start_time = millis();
          }
    
    
    if (!blade_found && currentTenzo >= pressure_to_find_blade && !making_ding && !pulling_blade && !prepearing_for_new_blade) { //лопатка найдена
      blade_found = true;
//      stepper_base.brake(); //вместо брейк теперь флаг разрешения движения
      base_run_flag = false;
      sendStatus();
      // Дополнительные действия при нахождении лезвия
    }
    
    if (blade_found && !pressure_reached && pulling_blade){ //логика натягивания лопатки
//      stepper_base.setTarget(circle_in_steps, ABSOLUTE);
//      stepper_base.tick();
      base_run_flag = true;
      updateTenzoData();
      
      if (currentTenzo >= pressure_threshold){ //условие того, что лопатка натянута
      pressure_reached = true;
//      stepper_base.brake();
      base_run_flag = false;
      pulling_blade = false;
      sendStatus();
        }
      
      }
  
    
    if (pressure_reached && making_ding){ //если дана команда на издание звука в парсере - издать звук
      
      if (!head_lifting){ //логика "заряжания" медиатора на поднятие
        head_lifting = true;
        stepper_head.reset();
        stepper_head.setSpeed(3000);     // задаем макс скорость для издавания звука
        stepper_head.setAcceleration(2000); 
        stepper_head.setMaxSpeed(8000);  // Максимальная скорость подъема
        stepper_head.setTarget(3200, RELATIVE);
      }
        
        
       if (head_lifting){ //логика поднятия медиатора
            head_falling = false;
            if(!stepper_head.tick()){ //за счет stepper_head.tick() происходит движение до ранее заданного значения которое находится в парсере комманд
            head_lifting = false;
            head_position = false; // Обновляем положение головки(головка опускается - выходит на нерабочее положение, поэтому head_position = false)
            pressure_reached = false;
            making_ding = false;
            wait_recording_start_time = millis();
            prepearing_for_new_blade = true; //если головка поднята - подготовить медиатор к поиску след. лопатки
            stepper_base.setTarget(blade_width, RELATIVE);
            sendStatus();
          }
        }
    
    }
    if (prepearing_for_new_blade){
      if (millis() - wait_recording_start_time >= prepearing_time){ //после того, как условие выполнится 1 раз, оно будет верно всегда 
          if(!stepper_base.tick() && !head_falling){
            head_falling = true; //опускаем головку после движения базы на ширину лопатки 
            stepper_head.reset();
        stepper_head.setSpeed(3000);     // задаем макс скорость для издавания звука
        stepper_head.setAcceleration(2000); 
        stepper_head.setMaxSpeed(8000);  // Максимальная скорость подъема
        stepper_head.setTarget(3200, RELATIVE);
            }
            
          else{
            }
            
          if (head_falling){ //опускаем головку после движения базы на ширину лопатки 
  
          head_lifting = false;
          if(!stepper_head.tick()){ //за счет stepper_head.tick() происходит движение до ранее заданного значения которое находится в парсере комманд
          head_falling = false;
          head_position = true; // Обновляем положение головки(головка опускается - выходит на нерабочее положение, поэтому head_position =  true)
          prepearing_for_new_blade = false;
          blade_found = false;
          stepper_base.setTarget(circle_in_steps, ABSOLUTE); // продолжаем двигаться к конечной точке равной полному кругу
          base_run_flag = true;
          sendStatus();

            }
          }
        }
      }
//    if ((millis() - find_blade_start_time >= serach_interval) && !blade_found) {
//      find_blade_in_progress = false;
//      if (head_position){//убеждаемся, что головка поднята и возвращаем базу
//      head_lifting = true;
//      }
//      return_base();
//
//    }
    
//    if(distance_traveled == circle_in_steps){
//      distance_traveled = 0;
//      find_blade_in_progress = false;
//      
//      if (head_position){ //убеждаемся, что головка поднята и возвращаем базу
//      head_lifting = true;
//      }
//      return_base();
//      }
  }
  
 if (head_lifting && !find_blade_in_progress){ //в режиме поиска лопатки свое собственное поднятие головки
    head_falling = false;
    if(!stepper_head.tick()){ //за счет stepper_head.tick() происходит движение до ранее заданного значения которое находится в парсере комманд
      head_lifting = false;
      head_position = false; // Обновляем положение головки(головка опускается - выходит на нерабочее положение, поэтому head_position = false)
      sendStatus(); 
    }
  }
  if (head_falling && !find_blade_in_progress){ //в режиме поиска лопатки свое собственное поднятие головки
    head_lifting = false;
    if(!stepper_head.tick()){
      head_falling = false;
      head_position = true; // Обновляем положение головки (головка опускается - выходит на рабочее положение, поэтому head_position = true)
       sendStatus();
    }
  } 
   if (base_returning && !head_position){ //сначала должна быть поднята головка
    if(!stepper_base.tick()){
    base_returning = false;
       //выставляем обратно заданные настройками значения
    stepper_base.setSpeed(speed_base);
    stepper_base.setAcceleration(accel_base); 
    stepper_base.setMaxSpeed(MaxSpeed_base);
    sendStatus();
    }
    
  }
  
}

// Обработка входящих данных и вызов обработчика JSON
void handleIncomingData() {
  if (Serial.available() > 0) {
    size_t len = Serial.readBytesUntil('\n', jsonBuffer, sizeof(jsonBuffer) - 1);
    jsonBuffer[len] = '\0';  // Завершаем строку
    Serial.println(jsonBuffer);

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
    TenzoUpdateRate = doc["ratset_base_settingse"].as<int>();
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
  } else if (strcmp(command, "move_head_up") == 0) { //новая логика поднятия головки, основанная на флагах(основное действие выполняется в loop для избегания лишних циклов while)
      if(!head_lifting && head_position == true && !find_blade_in_progress){
        head_lifting = true;
        stepper_head.reset();
        stepper_head.setSpeed(1000);     // Скорость подъема головки
        stepper_head.setAcceleration(1000); 
        stepper_head.setMaxSpeed(8000);  // Максимальная скорость подъема
        stepper_head.setTarget(-3200, RELATIVE);
        }
        
//      moveHeadUp(speed_head,accel_head,MaxSpeed_head);  // Поднять головку
  } else if (strcmp(command, "move_head_down") == 0) {//новая логика поднятия головки, основанная на флагах(основное действие выполняется в loop для избегания лишних циклов while)
      pressure_threshold = doc["pressure"].as<int>();  // Установить давление для остановки
      if(!head_falling && head_position == false && !find_blade_in_progress){
        head_falling = true;
        stepper_head.reset();
        stepper_head.setSpeed(1000);     // Скорость подъема головки
        stepper_head.setAcceleration(1000); 
        stepper_head.setMaxSpeed(8000);  // Максимальная скорость подъема
        stepper_head.setTarget(3200, RELATIVE);
        }
      
//      moveHeadDown(speed_head,accel_head,MaxSpeed_head);  // Опустить головку
  }
     else if (strcmp(command, "find_blade") == 0){
      find_blade();
      }
    else if (strcmp(command, "return_base") == 0){
      return_base();
      }
    else if (strcmp(command, "ding") == 0){
      if(find_blade_in_progress && pressure_reached){
        making_ding = true;
        sendStatus(); //там где изменяются флаги режимов вызывается отправка статуса
        }
      }
    else if (strcmp(command, "pull_blade") == 0){
      if(find_blade_in_progress && blade_found){
        pulling_blade = true;
        sendStatus();//там где изменяются флаги режимов вызывается отправка статуса
        }
      }
    else if (strcmp(command, "status") == 0){
      sendStatus(); //единожды запросить статус установки
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
//
//
//void controlMotors() {
//  if (head_position && (currentTenzo >= pressure_threshold)) {
//    moveHeadUp(speed_head,accel_head,MaxSpeed_head);  // Автоматически поднимаем головку, если давление превышено
//  }
//}

// Функция для подъема головки
void moveHeadUp(int start_speed,int accel, int MaxSpeed) {
  if (head_position == true){
  stepper_head.reset();
  stepper_head.setSpeed(1000);     // Скорость подъема головки
  stepper_head.setAcceleration(1000); 
  stepper_head.setMaxSpeed(8000);  // Максимальная скорость подъема
  stepper_head.setTarget(-3200, RELATIVE);
  head_position = false;

//  stepper_head.setTarget(-80000, RELATIVE);  // Подняться вверх
//  while (digitalRead(limitSwitchPin) == HIGH) {
//    stepper_head.tick();  // Выполняем движение до разжатия концевика
//  }
//  head_position = false;  // Обновляем состояние головки
//}
}
}
// Функция для опускания головки
void moveHeadDown(int start_speed,int accel, int MaxSpeed) {
  if (head_position == false){
  stepper_head.reset();
  stepper_head.setSpeed(1000);     // Скорость опускания головки
  stepper_head.setAcceleration(1000); 
  stepper_head.setMaxSpeed(8000);  // Максимальная скорость опускания
  //временный код
  stepper_head.setTarget(3200, RELATIVE); 
  head_position = true;
  }
//  stepper_head.setTarget(80000, RELATIVE);  // Опуститься вниз
//  while (digitalRead(limitSwitchPin) == LOW) {
//    stepper_head.tick();  // Выполняем движение до замыкания концевика
//  }
//  head_position = true;  // Обновляем состоянНекоие головки
//}
}


void find_blade(){
  if(blade_found == false && head_position  && !find_blade_in_progress){
    stepper_base.setSpeed(1000);
    stepper_base.setAcceleration(1000);
    stepper_base.setMaxSpeed(1500);
    find_blade_start_time = millis();
    stepper_base.setTarget(circle_in_steps, ABSOLUTE);
    find_blade_in_progress = true;
    sendStatus();
  }
}
//void ding(){
//  if(blade_found == true && head_position == true){
//    updateTenzoData();
//    while(currentTenzo < pressure_threshold){
//      stepper_base.tick();
//      }
//      stepper_base.brake();
//      moveHeadUp(speed_head,accel_head,MaxSpeed_head);  // Автоматически поднимаем головку, если давление превышено
//      blade_found == false;
//      sendStatus("ding");
//  }
//  }
// Отправка статуса в JSON формате
void return_base(){
//  if (head_position == true){//головка поднимается отдельно 
//      moveHeadUp(speed_head, accel_head,MaxSpeed_head);
//      blade_found == false;
//
//      }
    base_returning = true;
    stepper_base.setSpeed(400);     //выставляем макс скорость для быстрого возврата
    stepper_base.setAcceleration(400); //выставляем макс скорость для быстрого возврата
    stepper_base.setMaxSpeed(4000);//выставляем макс скорость для быстрого возврата
    
    stepper_base.setTarget(base_init_pos, ABSOLUTE); //задаем стартовую позицию
    sendStatus();
  
  }

void sendStatus() { //новый sendStatus теперь возвращает флаги режимов и работает по запросу(когда изменяются эти флаги режима), а не постоянно
    jsonDoc.clear();
    jsonDoc["find_blade_in_progress"] = find_blade_in_progress;
    jsonDoc["head_position"] = head_position ? "down" : "up";
    jsonDoc["blade_found"] = blade_found;
    jsonDoc["pulling_blade"] = pulling_blade;
    jsonDoc["pressure_reached"] = pressure_reached;
    jsonDoc["making_ding"] = making_ding;
    jsonDoc["prepearing_for_new_blade"] = prepearing_for_new_blade;
    jsonDoc["base_returning"] = base_returning;

  serializeJson(jsonDoc, Serial);  // Отправка JSON данных
  Serial.println();  // Завершающий символ строки

  
}
//void sendStatus(const char* command ) {
//  
//  if(status_flag){
//    if (millis() - LastStatusUpdate >= StatusUpdateRate){
//    LastStatusUpdate = millis();
//    jsonDoc.clear();
//    jsonDoc["current_weight"] = currentTenzo;
//    jsonDoc["base_motor_on"] = Is_motor_on;
//    jsonDoc["head_position"] = head_position ? "down" : "up";
//    jsonDoc["is_blade_found"] = blade_found;
//    jsonDoc["base_speed"] = speed_base;
//    jsonDoc["base_accel"] = accel_base;
//    jsonDoc["base_maxspeed"] = MaxSpeed_base;
//    jsonDoc["command"] = command;
//
//  serializeJson(jsonDoc, Serial);  // Отправка JSON данных
//  Serial.println();  // Завершающий символ строки
//
//  }
//  }
//}
// Установка начальных параметров двигателей
void setupMotors() {
  stepper_base.disable();//включаем двигатели
  stepper_head.disable();//включаем двигатели
  stepper_base.setRunMode(FOLLOW_POS);
  stepper_head.setRunMode(FOLLOW_POS);
  base_init_pos = stepper_head.getCurrent();
  
}
