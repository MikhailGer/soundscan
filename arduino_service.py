import json
import logging
import sys
from codeop import compile_command
from email.policy import default

from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import QMainWindow, QLabel, QPushButton, QVBoxLayout, QWidget, QApplication

from src.arduino.arduino_controller import ArduinoController
from src.arduino.arduino_worker import ArduinoWorker

from src.db import Session as DatabaseSession
from src.models import DeviceConfig


logging.basicConfig(
    level=logging.DEBUG,  # Установить уровень логирования
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Формат сообщений
    handlers=[
        logging.FileHandler("application.log"),  # Запись логов в файл
        logging.StreamHandler(sys.stdout)  # Вывод логов в консоль
    ]
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Создание объекта для работы с Arduino
        self.arduino_worker = ArduinoController().create_worker()
        self.arduino_worker.data_received.connect(self.on_data_received)  # Подключаем обработчик данных
        self.arduino_worker.connection_established.connect(
            self.on_connection_established)  # Подключаем обработчик состояния подключения

        # Интерфейс Qt
        self.label_status = QLabel("Подключение к Arduino...")
        self.button_connect = QPushButton("Подключить")
        self.button_connect.clicked.connect(self.connect_arduino)

        self.button_motor_on = QPushButton("Включить мотор базы")
        self.button_motor_off = QPushButton("Выключить мотор базы")
        self.button_move_head_up = QPushButton("Поднять головку")
        self.button_move_head_down = QPushButton("Опустить головку")
        self.button_ding = QPushButton("ding!")
        self.button_return_base = QPushButton("Вернуть базу на старт")
        self.button_find_blade = QPushButton("Найти лопатку")


        # Подключение кнопок к слотам
        self.button_motor_on.clicked.connect(self.start_base_motor)
        self.button_motor_off.clicked.connect(self.stop_base_motor)
        self.button_move_head_up.clicked.connect(self.move_head_up)
        self.button_move_head_down.clicked.connect(self.move_head_down)
        self.button_ding.clicked.connect(self.ding)
        self.button_return_base.clicked.connect(self.return_base)
        self.button_find_blade.clicked.connect(self.find_blade)
        # Макет
        layout = QVBoxLayout()
        layout.addWidget(self.label_status)
        layout.addWidget(self.button_connect)
        layout.addWidget(self.button_motor_on)
        layout.addWidget(self.button_motor_off)
        layout.addWidget(self.button_move_head_up)
        layout.addWidget(self.button_move_head_down)
        layout.addWidget(self.button_find_blade)
        layout.addWidget(self.button_ding)
        layout.addWidget(self.button_return_base)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # Деактивируем кнопки управления до подключения к Arduino
        self.set_control_buttons_state(False)
        self.connection_established = False
        # self.get_motors_settings_from_db()

    # Слот для подключения к Arduino
    @pyqtSlot()
    def connect_arduino(self):
        self.arduino_worker.start()  # Запуск потока

    # Обработка статуса подключения
    @pyqtSlot(bool)
    def on_connection_established(self, connected):
        if connected:
            self.connection_established = True
            self.label_status.setText("Подключено к Arduino!")
            self.set_control_buttons_state(True)
            self.get_motors_settings_from_db()

        else:
            self.label_status.setText("Ошибка подключения к Arduino.")

    # Обработка входящих данных от Arduino
    @pyqtSlot(str)
    def on_data_received(self, data):
        try:
            # Пытаемся разобрать строку как JSON
            json_data = json.loads(data)
            print(f"Получено от Arduino: {json_data}")
            # Обработка данных и обновление состояния интерфейса
            self.update_ui(json_data)
        except json.JSONDecodeError:
            print(f"Некорректные данные: {data}")

    # Обновление интерфейса на основе данных от Arduino
    def update_ui(self, data):
        # Пример обновления UI на основе полученных данных
        weight = data.get("current_weight", 0)
        motor_on = data.get("base_motor_on", False)
        head_position = data.get("head_position", "unknown")
        is_blade_found = data.get("is_blade_found")

        self.label_status.setText(
            f"Текущий вес: {weight} кг, Мотор базы: {'включен' if motor_on else 'выключен'}, Позиция головки: {head_position}, Лопатка найдена: {is_blade_found}")

    # Управление мотором базы
    def start_base_motor(self):
        command = {"command": "set_motor_on", "state": True}
        self.arduino_worker.send_command(command)
    def stop_base_motor(self):
        command = {"command": "set_motor_on", "state": False}
        self.arduino_worker.send_command(command)

    # Управление головкой
    def move_head_up(self):
        command = {"command": "move_head_up"}
        self.arduino_worker.send_command(command)

    def move_head_down(self):
        command = {"command": "move_head_down", "pressure": 10}  # Например, установить порог давления
        self.arduino_worker.send_command(command)

    def get_motors_settings_from_db(self):
        if self.connection_established:
            session = DatabaseSession()
            try:
                config = session.query(DeviceConfig).first()
                if config:
                    start_speed_head = config.head_motor_speed
                    accel_head = config.head_motor_accel
                    MaxSpeed_head = config.head_motor_MaxSpeed

                    start_speed_base = config.base_motor_speed
                    accel_base = config.base_motor_accel
                    MaxSpeed_base = config.base_motor_MaxSpeed
                    command = {"command": "set_head_settings", "speed": start_speed_head , "accel": accel_head, "MaxSpeed": MaxSpeed_head}
                    self.arduino_worker.send_command(command)
                    command = {"command": "set_base_settings", "speed": start_speed_base, "accel": accel_base,
                               "MaxSpeed": MaxSpeed_base}
                    self.arduino_worker.send_command(command)
                else:
                   self.set_default_motor_settings()
            finally:
                session.close()

    def set_default_motor_settings(self):
        defaults = DeviceConfig()
        command = {"command": "set_head_settings", "speed": defaults.head_motor_speed, "accel": defaults.head_motor_accel,
                   "MaxSpeed": defaults.head_motor_MaxSpeed}
        self.arduino_worker.send_command(command)
        command = {"command": "set_base_settings", "speed": defaults.base_motor_speed, "accel": defaults.base_motor_accel,
                   "MaxSpeed": defaults.base_motor_MaxSpeed}
        self.arduino_worker.send_command(command)

    def find_blade(self):
        command = {"command": "find_blade"}
        self.arduino_worker.send_command(command)

    def return_base(self):

        command = {"command": "return_base"}
        self.arduino_worker.send_command(command)

    def ding(self):
        command = {"command": "ding"}
        self.arduino_worker.send_command(command)

    # Включение/выключение кнопок управления
    def set_control_buttons_state(self, state):
        self.button_motor_on.setEnabled(state)
        self.button_motor_off.setEnabled(state)
        self.button_move_head_up.setEnabled(state)
        self.button_move_head_down.setEnabled(state)
        self.button_ding.setEnabled(state)
        self.button_return_base.setEnabled(state)
        self.button_find_blade.setEnabled(state)

    # Обработка закрытия окна и завершения потока
    def closeEvent(self, event):
        self.arduino_worker.stop()  # остановка потока перед выходом
        event.accept()


# Запуск приложения
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
