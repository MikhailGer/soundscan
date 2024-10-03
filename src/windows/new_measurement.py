import logging
from PyQt5.QtSerialPort import QSerialPort
from PyQt5.QtWidgets import QTableWidgetItem
from src.db import Session
from src.models import DiskType, Blade

# Настройка логирования
logger = logging.getLogger(__name__)



def load_disk_types_to_combobox(main_window):
    """
    Загрузка типов дисков в nm_disk_type.
    """
    logger.info("Загрузка типов дисков в ComboBox")
    session = Session()
    try:
        disk_types = session.query(DiskType).all()
        logger.info(f"Загружено {len(disk_types)} типов дисков из базы данных")

        main_window.nm_disk_type.clear()
        for disk_type in disk_types:
            main_window.nm_disk_type.addItem(disk_type.name, disk_type.id)
            logger.debug(f"Добавлен тип диска: {disk_type.name} (ID: {disk_type.id})")
    except Exception as e:
        logger.error(f"Ошибка при загрузке типов дисков: {e}")
    finally:
        session.close()


def set_controls_enabled(main_window, enabled):
    """
    Установка доступности элементов интерфейса.
    Если enabled = False, блокируются все элементы, кроме nm_stop.
    """
    logger.info(f"Установка доступности элементов интерфейса: {'Включены' if enabled else 'Отключены'}")
    main_window.tabWidget.setEnabled(enabled)
    main_window.nm_start.setEnabled(enabled)
    main_window.nm_disk_type.setEnabled(enabled)
    main_window.nm_measurements.setEnabled(enabled)
    main_window.nm_stop.setEnabled(not enabled)


def start_control(main_window, arduino):
    """
    Начало процесса контроля.
    """
    logger.info("Начало процесса контроля")
    set_controls_enabled(main_window, False)  # Блокируем элементы
    arduino.start_mode()  # Запуск контроля на Arduino
    logger.info("Отправка команды на старт контроля")

    session = Session()
    try:
        blades = session.query(Blade).filter_by(disk_type_id=main_window.nm_disk_type.currentData()).all()
        logger.info(f"Загружено {len(blades)} лопаток для контроля")

        # Заполнение таблицы измерений
        main_window.nm_measurements.setRowCount(len(blades))
        main_window.nm_measurements.setColumnCount(2)
        main_window.nm_measurements.setHorizontalHeaderLabels(["Номер лопатки", "Результат"])

        for row, blade in enumerate(blades):
            main_window.nm_measurements.setItem(row, 0, QTableWidgetItem(str(blade.num)))
            result = "Годен" if blade.prediction else "Не годен"
            main_window.nm_measurements.setItem(row, 1, QTableWidgetItem(result))
            logger.debug(f"Лопатка {blade.num}: {result}")
    except Exception as e:
        logger.error(f"Ошибка при обновлении данных лопаток: {e}")
    finally:
        session.close()


def stop_control(main_window, arduino):
    """
    Остановка процесса контроля.
    """
    logger.info("Остановка процесса контроля")
    arduino.stop_mode()  # Остановка контроля на Arduino
    set_controls_enabled(main_window, True)  # Разблокируем элементы
    logger.info("Контроль завершен и элементы интерфейса разблокированы")


def setup_new_measurement_tab(main_window, arduino):
    """
    Настройка логики вкладки "Новое измерение".
    """
    logger.info("Настройка вкладки 'Новое измерение'")
    main_window.nm_start.clicked.connect(lambda: start_control(main_window, arduino))
    main_window.nm_stop.clicked.connect(lambda: stop_control(main_window, arduino))

