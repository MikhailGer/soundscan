import sys
import os
import json
from PyQt5.QtCore import QThread, pyqtSignal, QObject, pyqtSlot
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QLabel
import serial
import time


# Класс для взаимодействия с Arduino в отдельном потоке
class ArduinoWorker(QThread):
    data_received = pyqtSignal(str)  # Сигнал для передачи данных в основной поток
    connection_established = pyqtSignal(bool)  # Сигнал для состояния подключения

    def __init__(self, port='COM3', baudrate=115200):
        super().__init__()
        print(f"ArduinoWorker port {port}")
        self.port = port
        self.baudrate = baudrate
        self.is_running = True
        self.arduino = None

    def run(self):
        # Подключение к Arduino
        try:

            if os.name == 'nt':  # Windows
                port_name = f"{self.port}"  # Например, 'COM3'
            else:  # Unix-подобные системы
                port_name = f"/dev/{self.port}"

            self.arduino = serial.Serial(port_name, self.baudrate, timeout=10)
            time.sleep(2)  # Задержка для установки соединения
            self.connection_established.emit(True)  # Сигнализируем, что подключение успешно
            print("Подключились")
        except Exception as e:
            print(f"Ошибка подключения: {e}")
            self.connection_established.emit(False)
            return

        # Основной цикл для чтения данных
        while self.is_running:
            if self.arduino.in_waiting > 0:
                try:
                    data = self.arduino.readline().decode().strip()
                    if data:
                        self.data_received.emit(data)
                except Exception as e:
                    print(f"Ошибка чтения: {e}")

    def send_command(self, command):
        try:
            json_command = json.dumps(command) + '\n'  # Преобразование команды в JSON и добавление новой строки
            self.arduino.write(json_command.encode())  # Отправка команды в Arduino
        except Exception as e:
            print(f"Ошибка отправки команды: {e}")

    def stop(self):
        self.is_running = False
        if self.arduino:
            self.arduino.close()


# Основной интерфейс приложения
# class MainWindow(QMainWindow):
#     def __init__(self):
#         super().__init__()
#
#         # Создание объекта для работы с Arduino
#         self.arduino_worker = ArduinoWorker()
#         self.arduino_worker.data_received.connect(self.on_data_received)  # Подключаем обработчик данных
#         self.arduino_worker.connection_established.connect(
#             self.on_connection_established)  # Подключаем обработчик состояния подключения
#
#         # Интерфейс Qt
#         self.label_status = QLabel("Подключение к Arduino...")
#         self.button_connect = QPushButton("Подключить")
#         self.button_connect.clicked.connect(self.connect_arduino)
#
#         self.button_motor_on = QPushButton("Включить мотор базы")
#         self.button_motor_off = QPushButton("Выключить мотор базы")
#         self.button_move_head_up = QPushButton("Поднять головку")
#         self.button_move_head_down = QPushButton("Опустить головку")
#
#         # Подключение кнопок к слотам
#         self.button_motor_on.clicked.connect(self.start_base_motor)
#         self.button_motor_off.clicked.connect(self.stop_base_motor)
#         self.button_move_head_up.clicked.connect(self.move_head_up)
#         self.button_move_head_down.clicked.connect(self.move_head_down)
#
#         # Макет
#         layout = QVBoxLayout()
#         layout.addWidget(self.label_status)
#         layout.addWidget(self.button_connect)
#         layout.addWidget(self.button_motor_on)
#         layout.addWidget(self.button_motor_off)
#         layout.addWidget(self.button_move_head_up)
#         layout.addWidget(self.button_move_head_down)
#
#         container = QWidget()
#         container.setLayout(layout)
#         self.setCentralWidget(container)
#
#         # Деактивируем кнопки управления до подключения к Arduino
#         self.set_control_buttons_state(False)
#
#     # Слот для подключения к Arduino
#     @pyqtSlot()
#     def connect_arduino(self):
#         self.arduino_worker.start()  # Запуск потока
#
#     # Обработка статуса подключения
#     @pyqtSlot(bool)
#     def on_connection_established(self, connected):
#         if connected:
#             self.label_status.setText("Подключено к Arduino!")
#             self.set_control_buttons_state(True)
#         else:
#             self.label_status.setText("Ошибка подключения к Arduino.")
#
#     # Обработка входящих данных от Arduino
#     @pyqtSlot(str)
#     def on_data_received(self, data):
#         try:
#             # Пытаемся разобрать строку как JSON
#             json_data = json.loads(data)
#             print(f"Получено от Arduino: {json_data}")
#             # Обработка данных и обновление состояния интерфейса
#             self.update_ui(json_data)
#         except json.JSONDecodeError:
#             print(f"Некорректные данные: {data}")
#
#     # Обновление интерфейса на основе данных от Arduino
#     def update_ui(self, data):
#         # Пример обновления UI на основе полученных данных
#         weight = data.get("current_weight", 0)
#         motor_on = data.get("base_motor_on", False)
#         head_position = data.get("head_position", "unknown")
#
#         self.label_status.setText(
#             f"Текущий вес: {weight} кг, Мотор базы: {'включен' if motor_on else 'выключен'}, Позиция головки: {head_position}")
#
#     # Управление мотором базы
#     def start_base_motor(self):
#         command = {"command": "set_motor_on", "state": True}
#         self.arduino_worker.send_command(command)
#
#     def stop_base_motor(self):
#         command = {"command": "set_motor_on", "state": False}
#         self.arduino_worker.send_command(command)
#
#     # Управление головкой
#     def move_head_up(self):
#         command = {"command": "move_head_up"}
#         self.arduino_worker.send_command(command)
#
#     def move_head_down(self):
#         command = {"command": "move_head_down", "pressure": 10}  # Например, установить порог давления
#         self.arduino_worker.send_command(command)
#
#     # Включение/выключение кнопок управления
#     def set_control_buttons_state(self, state):
#         self.button_motor_on.setEnabled(state)
#         self.button_motor_off.setEnabled(state)
#         self.button_move_head_up.setEnabled(state)
#         self.button_move_head_down.setEnabled(state)
#
#     # Обработка закрытия окна и завершения потока
#     def closeEvent(self, event):
#         self.arduino_worker.stop()  #Остановка потока перед выходом
#         event.accept()