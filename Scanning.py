from venv import logger
import json
import logging
import sys
from codeop import compile_command
from email.policy import default

from datetime import datetime
import time

import io
import wave
import pyaudio

from PyQt5.QtCore import QObject
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

class Scanning(QObject):
    scanning_finished = pyqtSignal()
    blade_found = pyqtSignal()

    def __init__(self, disk_type_id,arduino_worker):
        super().__init__()
        self.recording_duration = 5
        self.num = 0
        self.blade_created = False
        self.data_updated = False
        self.base_returning = None
        self.preparing_for_new_blade = None
        self.making_ding = None
        self.pressure_reached = None
        self.pulling_blade = None
        self.head_position = None
        self.blade_found = None
        self.scan_in_progress = None

        self.blade_force = None
        self.disk_scan_id = None
        self.disk_type_id = disk_type_id
        self.is_running = False

        # Создание объекта для работы с Arduino
        self.arduino_worker = arduino_worker
        self.arduino_worker.data_received.connect(self.on_data_received)  # Подключаем обработчик данных
        self.connection_established = self.arduino_worker.connection_established
        self.arduino_worker.connection_established.connect(self.on_connection_established)
        # if self.connection_established:
        #     self.get_motors_settings_from_db()
        #     self.start_base_motor()
        #     self.status()

    # Обработка входящих данных от Arduino
    @pyqtSlot(str)
    def on_data_received(self, data):
        try:
            # Пытаемся разобрать строку как JSON
            json_data = json.loads(data)
            print(f"Получено от Arduino: {json_data}")
            # Обработка данных и обновление состояния интерфейса
            self.update_status(json_data)
            self.process_state()
        except json.JSONDecodeError:
            print(f"Некорректные данные: {data}")

    @pyqtSlot(bool)
    def on_connection_established(self, connected):
        if connected:
            self.connection_established = True
        else:
            self.stop() #в случае отключения платы остановить
            logger.error("Ошибка подключения к Arduino. Аварийная остановка")

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
        self.scan_in_progress = data.get("scan_in_progress", "unknown")
        self.blade_found = data.get("blade_found", "unknown")
        self.head_position = data.get("head_position", "unknown")
        self.pulling_blade = data.get("pulling_blade", "unknown")
        self.pressure_reached = data.get("pressure_reached", "unknown")
        self.making_ding = data.get("making_ding", "unknown")
        self.preparing_for_new_blade = data.get("prepearing_for_new_blade", "unknown")
        self.base_returning = data.get("base_returning", "unknown")
        self.data_updated = True
        logger.info("Scanning process: Данные обновлены")
        if self.base_returning:
            self.scanning_finished.emit()

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

            self.get_motors_settings_from_db()
            self.start_base_motor()
            self.status()
        else:
            logger.error("Ошибка старта сканирования: устройство не подключено")

    def start_base_motor(self):
        command = {"command": "set_motor_on", "state": True}
        self.arduino_worker.send_command(command)
    def stop_base_motor(self):
        command = {"command": "set_motor_on", "state": False}
        self.arduino_worker.send_command(command)

    def move_head_up(self):
        command = {"command": "move_head_up"}
        self.arduino_worker.send_command(command)

    def move_head_down(self, blade_force):
        command = {"command": "move_head_down", "pressure": blade_force}  # Например, установить порог давления
        self.arduino_worker.send_command(command)

    def start_command(self):
        command = {"command": "start_scan"}
        self.arduino_worker.send_command(command)

    def return_base(self):

        command = {"command": "return_base"}
        self.arduino_worker.send_command(command)

    def ding(self):
        logger.info("Scanning: Выполняется команда ding")
        command = {"command": "ding"}
        self.arduino_worker.send_command(command)

    def pull(self):
        logger.info("Scanning:выполняется команда pull")
        command = {"command": "pull_blade"}
        self.arduino_worker.send_command(command)

    def status(self):
        logger.info("Scanning:выполняется команда status")
        command = {"command": "status"}
        self.arduino_worker.send_command(command)
        self.data_updated = False
        logger.info("Scanning proccess: Запрос на обновление данных")

    def process_state(self):
        if not self.scan_in_progress:
            if self.head_position == "up":
                self.move_head_down(self.blade_force)
            else:
                self.start_command()
        else:
            if self.blade_found:
                if not self.blade_created:
                    self.blade_created = True
                    self.num += 1
                if not self.pressure_reached:
                    if not self.pulling_blade:
                        self.pull()
                else:
                    self.ding()
                    wav_data = self.start_recording()
                    new_blade = Blade(
                        disk_scan_id=self.disk_scan_id,
                        num=self.num,
                        scan=wav_data,
                        prediction=False  # Для имитации работы ML
                    )
                    self.session.add(new_blade)
                    self.session.commit()
                    #тут логика старта записи микрофона, добавления записи в бд и добавление звука в потокобезопасную очередь для отправки в МЛ на анализ
                    #тут логика создания экземпляра blade c полными данными в бд (позже) (сначала ML даст ответ а затем создастся экземпляр)
                    #для имитации работы ML пусть просто будет строчка prediction = false

                    self.blade_created = False

    def start_recording(self):
        # Инициализируем запись аудио
        import pyaudio

        CHUNK = 1024
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 44100
        RECORD_SECONDS = self.recording_duration  # Длительность записи соответствует длительности ding

        p = pyaudio.PyAudio()

        stream = p.open(format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        frames_per_buffer=CHUNK)

        logger.info("* Начало записи")

        frames = []

        for _ in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
            data = stream.read(CHUNK)
            frames.append(data)

        logger.info("* Конец записи")

        stream.stop_stream()
        stream.close()
        p.terminate()

        audio_buffer = io.BytesIO()
        wf = wave.open(audio_buffer, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
        wf.close()
        # Преобразуем аудиоданные
        wav_data = audio_buffer.getvalue()
        return wav_data


    def stop_scan(self):
        self.return_base()
        self.scanning_finished.emit()


