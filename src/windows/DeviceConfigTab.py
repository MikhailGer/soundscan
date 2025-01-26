import logging
from math import trunc
from operator import truediv

from PyQt5.QtWidgets import QMessageBox, QWidget
from sqlalchemy.orm import Session
from src.db import Session as DatabaseSession
from src.models import DeviceConfig
import serial.tools.list_ports

# Настройка логгера для модуля
logger = logging.getLogger(__name__)

class DeviceConfigTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.session = None
        self.signals_connected = False

    def connect_signals(self):
        #Подключаем события
        if not self.signals_connected:
            self.main_window.dc_save.clicked.connect(self.save_device_config)
            self.signals_connected = True

        logger.info("Настройка вкладки 'Параметры установки' завершена, сигналы включены")

    def disconnect_signals(self):
        #Подключаем события
        if self.signals_connected:
            self.main_window.dc_save.clicked.disconnect(self.save_device_config)
            self.signals_connected = False

            logger.info("'Параметры установки', сигналы отключены")

    def start_tab(self):
        logger.info("вкладка 'Конфигурация устройства ': отрисовка")
        self.load_device_config()

    def load_device_config(self):
        """
        Загрузка конфигурации устройства и обновление интерфейса.
        """
        logger.info("Загрузка конфигурации устройства")
        config = self.fetch_device_config()
        if config:
            self.update_ui_with_config(config)
        else:
            self.show_error_message("Конфигурация устройства не найдена в базе данных.")

    def fetch_device_config(self):
        """
        Извлечение конфигурации устройства из базы данных.
        """
        self.session = DatabaseSession()
        try:
            config = self.session.query(DeviceConfig).first()
            if config:
                logger.info(f"Конфигурация устройства загружена: {config}")
            else:
                logger.warning("Конфигурация устройства не найдена в базе данных")
            return config
        except Exception as e:
            logger.error(f"Ошибка при загрузке конфигурации устройства: {e}")
            return None
        finally:
            self.session.close()

    def update_ui_with_config(self, config):
        """
        Обновление интерфейса значениями из конфигурации устройства.
        """
        # Получение доступных USB портов
        ports = list(serial.tools.list_ports.comports())
        port_names = [port.device for port in ports]
        logger.info(f"Доступные USB порты: {port_names}")

        # Заполнение ComboBox для USB портов
        self.update_combobox(self.main_window.dc_operating_port, port_names)

        # Заполнение ComboBox стандартными baud rates
        baud_rates = ['9600', '19200', '38400', '57600', '115200', '230400', '460800', '921600']
        self.update_combobox(self.main_window.dc_serial_baud_rate, baud_rates)

        # Обновление значений интерфейса
        self.main_window.dc_operating_port.setCurrentText(config.operating_port if config.operating_port in port_names else "")
        self.main_window.dc_serial_baud_rate.setCurrentText(str(config.SerialBaudRate) if str(config.SerialBaudRate) in baud_rates else '115200')

        self.main_window.dc_base_diameter.setText(str(config.base_diameter))
        self.main_window.dc_base_motor_speed.setText(str(config.base_motor_speed))
        self.main_window.dc_base_motor_accel.setText(str(config.base_motor_accel))
        self.main_window.dc_base_motor_max_speed.setText(str(config.base_motor_MaxSpeed))
        self.main_window.dc_head_motor_speed.setText(str(config.head_motor_speed))
        self.main_window.dc_head_motor_accel.setText(str(config.head_motor_accel))
        self.main_window.dc_head_motor_max_speed.setText(str(config.head_motor_MaxSpeed))
        self.main_window.dc_head_motor_returning_speed.setText(str(config.head_motor_returning_speed))
        self.main_window.dc_head_motor_returning_accel.setText(str(config.head_motor_returning_accel))
        self.main_window.dc_tenzo_update_rate.setText(str(config.tenzo_update_rate))
        self.main_window.dc_circle_length.setText(str(config.circle_in_steps))
        self.main_window.dc_search_time.setText(str(config.searching_time))
        self.main_window.dc_recording_time.setText(str(config.recording_time))
        self.main_window.dc_pressure_to_find.setText(str(config.force_to_find))

    def save_device_config(self):
        """
        Сохранение изменений конфигурации устройства в базу данных с проверкой корректности данных.
        """
        logger.info("Сохранение конфигурации устройства")
        self.session = DatabaseSession()
        try:
            config = self.session.query(DeviceConfig).first()

            if config:
                try:
                    serial_baud_rate = int(self.main_window.dc_serial_baud_rate.currentText()) or 115200
                    base_diameter = float(self.main_window.dc_base_diameter.text()) or 500.24
                    base_motor_speed = float(self.main_window.dc_base_motor_speed.text()) or 1.0
                    base_motor_accel = float(self.main_window.dc_base_motor_accel.text()) or 1.0
                    base_motor_max_speed = float(self.main_window.dc_base_motor_max_speed.text()) or 1.0
                    head_motor_speed = float(self.main_window.dc_head_motor_speed.text()) or 1.0
                    head_motor_accel = float(self.main_window.dc_head_motor_accel.text()) or 1.0
                    head_motor_max_speed = float(self.main_window.dc_head_motor_max_speed.text()) or 1.0
                    head_motor_returning_speed = float(self.main_window.dc_head_motor_returning_speed.text()) or 1.0
                    head_motor_returning_accel = float(self.main_window.dc_head_motor_returning_accel.text()) or 1.0
                    tenzo_update_rate = int(self.main_window.dc_tenzo_update_rate.text()) or 10

                    circle_in_steps = int(self.main_window.dc_circle_length.text()) or 14400
                    searching_time = int(self.main_window.dc_search_time.text()) or 10000
                    recording_time = int(self.main_window.dc_recording_time.text()) or 3000
                    force_to_find = int(self.main_window.dc_pressure_to_find.text()) or 50

                except ValueError as e:
                    logger.warning(f"Некорректное значение: {e}")
                    self.show_error_message("Пожалуйста, введите корректные числовые значения.")
                    return

                config.operating_port = self.main_window.dc_operating_port.currentText()
                config.SerialBaudRate = serial_baud_rate
                config.base_diameter = base_diameter
                config.base_motor_speed = base_motor_speed
                config.base_motor_accel = base_motor_accel
                config.base_motor_MaxSpeed = base_motor_max_speed
                config.head_motor_speed = head_motor_speed
                config.head_motor_accel = head_motor_accel
                config.head_motor_MaxSpeed = head_motor_max_speed
                config.head_motor_returning_speed = head_motor_returning_speed
                config.head_motor_returning_accel = head_motor_returning_accel
                config.tenzo_update_rate = tenzo_update_rate
                config.circle_in_steps = circle_in_steps
                config.searching_time = searching_time
                config.recording_time = recording_time
                config.force_to_find = force_to_find

                self.session.commit()
                logger.info("Конфигурация устройства успешно сохранена")
                self.show_info_message("Изменения успешно сохранены.")
            else:
                logger.error("Конфигурация устройства не найдена")
                self.show_error_message("Конфигурация устройства не найдена.")
        except Exception as e:
            logger.error(f"Ошибка при сохранении конфигурации: {e}")
        finally:
            self.session.close()

    def update_combobox(self, combobox, items):
        """
        Обновляет содержимое ComboBox.
        """
        combobox.clear()
        combobox.addItems(items)

    def show_error_message(self, message):
        """
        Показать сообщение об ошибке.
        """
        logger.error(f"Показ сообщения об ошибке: {message}")
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setText(message)
        msg.setWindowTitle("Ошибка")
        msg.exec_()

    def show_info_message(self, message):
        """
        Показать информационное сообщение.
        """
        logger.info(f"Показ информационного сообщения: {message}")
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setText(message)
        msg.setWindowTitle("Успех")
        msg.exec_()

