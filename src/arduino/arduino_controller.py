import logging
import time

from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from PyQt5.QtSerialPort import QSerialPort, QSerialPortInfo

from src.arduino.arduino_worker import ArduinoWorker
# from src.arduino.port_checker import PortChecker
from src.db import Session as DatabaseSession
from src.models import DeviceConfig

# Логирование
logger = logging.getLogger(__name__)


class ArduinoController():
    def __init__(self):
        self.serial = QSerialPort()
        self.port_name = None  # Текущий используемый порт

        logger.info("Инициализация ArduinoController.")
        # Загружаем порт из базы и пытаемся подключиться
        self.load_port_from_db()
        if not self.port_name:
            self.auto_connect()
        if not self.port_name:
            logger.warning("Портов для подключения ARDUINO не обнаружено")

    def create_worker(self):
        return ArduinoWorker(self.port_name)

    def load_port_from_db(self):
        """
        Загружаем порт и SerialBaudRate из базы данных и пробуем подключиться.
        """
        session = DatabaseSession()
        try:
            config = session.query(DeviceConfig).first()
            if config:
                logger.info(f"Попытка подключения к порту из базы данных: {config.operating_port}")
                self.connect_to_device(config.operating_port, config.SerialBaudRate)
            else:
                logger.warning("Конфигурация не найдена. Создаем конфигурацию с дефолтными значениями.")
                default_config = DeviceConfig()
                session.add(default_config)
                session.commit()
                self.connect_to_device(default_config.operating_port, default_config.SerialBaudRate)
        finally:
            session.close()

    def save_port_to_db(self, port_name, baud_rate):
        """
        Сохранение нового порта в базу данных.
        """
        session = DatabaseSession()
        try:
            config = session.query(DeviceConfig).first()
            if config:
                config.operating_port = port_name
                config.SerialBaudRate = baud_rate
                session.commit()
                logger.info(f"Порт {port_name} и скорость {baud_rate} сохранены в базе данных.")
            else:
                new_config = DeviceConfig(operating_port=port_name, SerialBaudRate=baud_rate)
                session.add(new_config)
                session.commit()
                logger.info(f"Создана новая конфигурация с портом {port_name} и скоростью {baud_rate}.")
        finally:
            session.close()

    def connect_to_device(self, port_name, baud_rate):
        """
        Подключение к устройству по указанному порту и скорости передачи данных.
        """
        self.serial.setPortName(port_name)
        self.serial.setBaudRate(baud_rate)

        if self.serial.open(QSerialPort.ReadWrite):
            logger.info(f"Подключение к {port_name} успешно.")
            self.port_name = port_name
        else:
            logger.warning(f"Не удалось подключиться к {port_name}. Запуск автоматического поиска.")

    def auto_connect(self):
        """
        Cканирования портов.
        Автоматическое подключение к Arduino, если устройство найдено на другом порту.
        """
        port_list = []
        logger.info("Запуск сканирования портов.")

        ports = QSerialPortInfo.availablePorts()

        # Логирование всех найденных портов и их свойств
        for port in ports:
            if not port.manufacturer:
                continue
            port_list.append(port)
            logger.debug(f"Обнаружен порт: {port.portName()} - {port.description()}, "
                         f"Производитель: {port.manufacturer()}")
        if not port_list:
            logger.info(f"Сканирование завершено. Портов не обнаружено.")
            return
        else:
            logger.info(f"Сканирование завершено. Обнаруженные порты: {port_list}")

        logger.info(f"Подключение к найденным портам")
        for port in port_list:
            logger.info(f"Проверка порта: {port}")
            # self.connect_to_device(port, 115200)#исправлена ошибка - вместо имени порта отправлялся объект порта
            self.connect_to_device(port.portName(), 115200)
            if self.serial.isOpen():
                self.serial.close()
                # self.save_port_to_db(port, 115200)исправлена ошибка - вместо имени порта отправлялся объект порта
                self.save_port_to_db(port.portName(), 115200)
                break