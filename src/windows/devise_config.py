import logging
from PyQt5.QtWidgets import QMessageBox
from sqlalchemy.orm import Session
from src.db import Session as DatabaseSession
from src.models import DeviceConfig
import serial.tools.list_ports

# Настройка логгера для модуля
logger = logging.getLogger(__name__)


def setup_device_config_tab(main_window):
    """
    Настройка логики для вкладки "Параметры установки".
    """
    logger.info("Настройка вкладки 'Параметры установки'")
    main_window.dc_save.clicked.connect(lambda: save_device_config(main_window))

# теперь on_tab_changed вызывается 1 раз при инициализации приложения и управляет вкладками

# def on_tab_changed(main_window, index):
#     """
#     Событие при переключении вкладок. Загружаем данные конфигурации устройства.
#     """
#     if index == main_window.tabWidget.indexOf(main_window.devise_config):
#         logger.info("Вкладка 'Параметры установки' активна, загружаем конфигурацию устройства")
#         load_device_config(main_window)


def load_device_config(main_window):
    """
    Загрузка конфигурации устройства из таблицы device_config и заполнение ComboBox значениями USB-портов и baud rates.
    """
    logger.info("Загрузка конфигурации устройства")
    session = DatabaseSession()
    try:
        config = session.query(DeviceConfig).first()
        if config:
            logger.info(f"Конфигурация устройства загружена: {config}")
        else:
            logger.warning("Конфигурация устройства не найдена в базе данных")

        # Получение доступных USB портов
        ports = list(serial.tools.list_ports.comports())
        port_names = [port.device for port in ports]
        logger.info(f"Доступные USB порты: {port_names}")

        # Заполнение ComboBox для USB портов
        main_window.dc_operating_port.clear()
        main_window.dc_operating_port.addItems(port_names)

        # Заполнение ComboBox стандартными baud rates
        baud_rates = ['9600', '19200', '38400', '57600', '115200', '230400', '460800', '921600']
        main_window.dc_serial_baud_rate.clear()
        main_window.dc_serial_baud_rate.addItems(baud_rates)

        if config:
            # Заполнение полей значениями из базы данных
            main_window.dc_operating_port.setCurrentText(config.operating_port if config.operating_port in port_names else "")
            main_window.dc_serial_baud_rate.setCurrentText(str(config.SerialBaudRate) if str(config.SerialBaudRate) in baud_rates else '115200')

            main_window.dc_base_diameter.setText(str(config.base_diameter))
            main_window.dc_base_motor_speed.setText(str(config.base_motor_speed))
            main_window.dc_base_motor_accel.setText(str(config.base_motor_accel))
            main_window.dc_base_motor_max_speed.setText(str(config.base_motor_MaxSpeed))
            main_window.dc_head_motor_speed.setText(str(config.head_motor_speed))
            main_window.dc_head_motor_accel.setText(str(config.head_motor_accel))
            main_window.dc_head_motor_max_speed.setText(str(config.head_motor_MaxSpeed))
            main_window.dc_head_motor_returning_speed.setText(str(config.head_motor_returning_speed))
            main_window.dc_head_motor_returning_accel.setText(str(config.head_motor_returning_accel))
            main_window.dc_tenzo_update_rate.setText(str(config.tenzo_update_rate))
            main_window.dc_circle_length.setText(str(config.circle_in_steps))
            main_window.dc_search_time.setText(str(config.searching_time))
            main_window.dc_recording_time.setText(str(config.recording_time))
            main_window.dc_pressure_to_find.setText(str(config.force_to_find))
        else:
            show_error_message("Конфигурация устройства не найдена в базе данных.")
    except Exception as e:
        logger.error(f"Ошибка при загрузке конфигурации устройства: {e}")
    finally:
        session.close()


def save_device_config(main_window):
    """
    Сохранение изменений конфигурации устройства в базу данных с проверкой корректности данных.
    """
    logger.info("Сохранение конфигурации устройства")
    session = DatabaseSession()
    try:
        config = session.query(DeviceConfig).first()

        if config:
            # Проверка на пустые или некорректные значения
            try:
                serial_baud_rate = int(main_window.dc_serial_baud_rate.currentText()) if main_window.dc_serial_baud_rate.currentText() else 115200
                base_diameter = float(main_window.dc_base_diameter.text()) if main_window.dc_base_diameter.text() else 500.24
                base_motor_speed = float(main_window.dc_base_motor_speed.text()) if main_window.dc_base_motor_speed.text() else 1.0
                base_motor_accel = float(main_window.dc_base_motor_accel.text()) if main_window.dc_base_motor_accel.text() else 1.0
                base_motor_max_speed = float(main_window.dc_base_motor_max_speed.text()) if main_window.dc_base_motor_max_speed.text() else 1.0
                head_motor_speed = float(main_window.dc_head_motor_speed.text()) if main_window.dc_head_motor_speed.text() else 1.0
                head_motor_accel = float(main_window.dc_head_motor_accel.text()) if main_window.dc_head_motor_accel.text() else 1.0
                head_motor_max_speed = float(main_window.dc_head_motor_max_speed.text()) if main_window.dc_head_motor_max_speed.text() else 1.0
                head_motor_returning_speed = float(main_window.dc_head_motor_returning_speed.text()) if main_window.dc_head_motor_returning_speed.text() else 1.0
                head_motor_returning_accel = float(main_window.dc_head_motor_returning_accel.text()) if main_window.dc_head_motor_returning_accel.text() else 1.0
                tenzo_update_rate = int(main_window.dc_tenzo_update_rate.text()) if main_window.dc_tenzo_update_rate.text() else 10

                circle_in_steps = int(main_window.dc_circle_length.text()) if main_window.dc_circle_length.text() else 14400
                searching_time = int(main_window.dc_search_time.text()) if main_window.dc_search_time.text() else 10000
                recording_time = int(main_window.dc_recording_time.text()) if main_window.dc_recording_time.text() else 3000
                force_to_find = int(main_window.dc_pressure_to_find.text()) if main_window.dc_pressure_to_find.text() else 50

            except ValueError as e:
                logger.warning(f"Некорректное значение: {e}")
                show_error_message("Пожалуйста, введите корректные числовые значения.")
                return

            # Обновляем значения в объекте конфигурации
            config.operating_port = main_window.dc_operating_port.currentText()
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

            # Сохраняем изменения в базе данных
            session.commit()
            logger.info("Конфигурация устройства успешно сохранена")
            show_info_message("Изменения успешно сохранены.")
        else:
            logger.error("Конфигурация устройства не найдена")
            show_error_message("Конфигурация устройства не найдена.")
    except Exception as e:
        logger.error(f"Ошибка при сохранении конфигурации: {e}")
    finally:
        session.close()


def show_error_message(message):
    """
    Показать сообщение об ошибке.
    """
    logger.error(f"Показ сообщения об ошибке: {message}")
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Critical)
    msg.setText(message)
    msg.setWindowTitle("Ошибка")
    msg.exec_()


def show_info_message(message):
    """
    Показать информационное сообщение.
    """
    logger.info(f"Показ информационного сообщения: {message}")
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Information)
    msg.setText(message)
    msg.setWindowTitle("Успех")
    msg.exec_()
