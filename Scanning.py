from venv import logger

from PyQt5.QtCore import QThread
import json
import logging
import sys
from codeop import compile_command
from email.policy import default

from datetime import datetime
import time

from PyQt5.QtCore import pyqtSlot, pyqtSignal

from src.arduino.arduino_controller import ArduinoController
from src.arduino.arduino_worker import ArduinoWorker

from src.db import Session as DatabaseSession
from src.models import DeviceConfig
from src.models import DiskScan, Blade, DiskType


logging.basicConfig(
    level=logging.DEBUG,  # Установить уровень логирования
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Формат сообщений
    handlers=[
        logging.FileHandler("application.log"),  # Запись логов в файл
        logging.StreamHandler(sys.stdout)  # Вывод логов в консоль
    ]
)

class Scanning(QThread):
    scanning_finished= pyqtSignal()
    blade_found = pyqtSignal(object)

    def __init__(self, disk_type_id,arduino_worker):
        super().__init__()

        self.data_updated = False
        self.base_returning = None
        self.preparing_for_new_blade = None
        self.making_ding = None
        self.pressure_reached = None
        self.pulling_blade = None
        self.head_position = None
        self.blade_found = None
        self.find_blade_in_progress = None

        self.blade_force = None
        self.disk_scan_id = None
        self.disk_type_id = disk_type_id
        self.is_running = False

        # Создание объекта для работы с Arduino
        self.arduino_worker = arduino_worker
        self.arduino_worker.data_received.connect(self.on_data_received)  # Подключаем обработчик данных
        self.connection_established = self.arduino_worker.connection_established
        self.arduino_worker.connection_established.connect(self.on_connection_established)
        if self.connection_established:
            self.get_motors_settings_from_db()
            self.status()

    # Обработка входящих данных от Arduino
    @pyqtSlot(str)
    def on_data_received(self, data):
        try:
            # Пытаемся разобрать строку как JSON
            json_data = json.loads(data)
            print(f"Получено от Arduino: {json_data}")
            # Обработка данных и обновление состояния интерфейса
            self.update_status(json_data)
        except json.JSONDecodeError:
            print(f"Некорректные данные: {data}")

    @pyqtSlot(bool)
    def on_connection_established(self, connected):
        if connected:
            self.connection_established = True
        else:
            self.stop() #в случае отключения платы остановить
            logger.info("Ошибка подключения к Arduino. Аварийная остановка")

    def get_motors_settings_from_db(self):
        print("get_motors_settings_from_db")
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
                command = {"command": "set_head_settings", "speed": start_speed_head, "accel": accel_head, "MaxSpeed": MaxSpeed_head}
                self.arduino_worker.send_command(command)

                command = {"command": "set_base_settings", "speed": start_speed_base, "accel": accel_base,
                           "MaxSpeed": MaxSpeed_base}
                time.sleep(0.1) #БЕЗ ЗАДЕРКИ ВЕСЬ ПАРСИНГ С АРДУИНО СЫПЕТСЯ (перенес в воркер, для подстраховки оставил и здесь)

                self.arduino_worker.send_command(command)


            else:
               self.set_default_motor_settings()
        finally:
            session.close()

    def update_status(self, data):
        self.find_blade_in_progress = data.get("find_blade_in_progress", "unknown")
        self.blade_found = data.get("blade_found", "unknown")
        self.head_position = data.get("head_position", "unknown")
        self.pulling_blade = data.get("pulling_blade", "unknown")
        self.pressure_reached = data.get("pressure_reached", "unknown")
        self.making_ding = data.get("making_ding", "unknown")
        self.preparing_for_new_blade = data.get("prepearing_for_new_blade", "unknown")
        self.base_returning = data.get("base_returning", "unknown")
        self.data_updated = True
        logger.error("Scanning proccess: Данные обновлены")

    def set_default_motor_settings(self):
        defaults = DeviceConfig()
        command = {"command": "set_head_settings", "speed": defaults.head_motor_speed, "accel": defaults.head_motor_accel,
                   "MaxSpeed": defaults.head_motor_MaxSpeed}
        self.arduino_worker.send_command(command)
        command = {"command": "set_base_settings", "speed": defaults.base_motor_speed, "accel": defaults.base_motor_accel,
                   "MaxSpeed": defaults.base_motor_MaxSpeed}
        self.arduino_worker.send_command(command)

    def start_scan(self):
        if self.connection_established:
            session = DatabaseSession()
            try:
                new_disk_scan = DiskScan(
                    name=f"{datetime.now()} New disc_scan",
                    disk_type_id=self.disk_type_id,
                    is_training=False
                )
                session.add(new_disk_scan)
                session.commit()
                logger.error(f"Создан DiskScan c id {new_disk_scan.id} относящийся к DiskType {new_disk_scan.disk_type_id}")
                self.disk_scan_id = new_disk_scan.id

                # Получаем blade_force из DiskType
                disk_type = session.query(DiskType).get(self.disk_type_id)
                if disk_type:
                    self.blade_force = disk_type.blade_force
                else:
                    logger.error(f"DiskType с id {self.disk_type_id} не найден.")
            except Exception as e:
                logger.error("Ошибка создания экземпляра сканирования или получения blade_force: %s", e, exc_info=True)
            finally:
                session.close()

            # Запуск сканирования
            try:
                self.is_running = True
                self.start()
                logger.error("Успех запуска сканирования")
            except Exception as e:
                logger.error("Ошибка старта сканирования: %s", e, exc_info=True)
        else:
            logger.error("Ошибка старта сканирования: устройство не подключено")


    def find_blade(self):
        command = {"command": "find_blade"}
        self.arduino_worker.send_command(command)

    def return_base(self):

        command = {"command": "return_base"}
        self.arduino_worker.send_command(command)

    def ding(self):
        command = {"command": "ding"}
        self.arduino_worker.send_command(command)

    def pull(self):
        command = {"command": "pull_blade"}
        self.arduino_worker.send_command(command)

    def status(self):
        command = {"command": "status"}
        self.arduino_worker.send_command(command)
        self.data_updated = False
        logger.error("Scanning proccess: Запрос на обновление данных")

    def run(self):
        while self.is_running and self.connection_established:
            # self.status()
                    # if not self.find_blade_in_progress:
            print(
                self.base_returning,
                self.preparing_for_new_blade,
                self.making_ding,
                self.pressure_reached,
                self.pulling_blade,
                self.head_position,
                self.blade_found,
                self.find_blade_in_progress,

            )
            time.sleep(1)



    def stop(self):
        self.is_running = False
        self.quit()
        self.wait()