import logging
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QListWidgetItem, QTableWidgetItem, QHeaderView

from src.db import Session
from src.models import DiskType, DiskScan, Blade

# Настройка логгера для модуля
logger = logging.getLogger(__name__)


def setup_change_history_tab(main_window):
    """
    Настройка логики для вкладки "История измерений".
    """
    logger.info("Настройка логики вкладки 'История измерений'")
    # Привязываем события
    main_window.tabWidget.currentChanged.connect(lambda index: on_tab_changed(main_window, index))
    main_window.ch_disk_type.currentIndexChanged.connect(lambda: update_measurements(main_window))
    main_window.ch_measurements.itemSelectionChanged.connect(lambda: update_blade_results(main_window))


def on_tab_changed(main_window, index):
    """
    Событие при переключении вкладок. Обновляем ComboBox с типами дисков.
    """
    logger.info(f"Переключение на вкладку с индексом {index}")
    if index == main_window.tabWidget.indexOf(main_window.change_history):
        logger.info("Вкладка 'История измерений' активна, обновляем список типов дисков")
        update_disk_type_combobox(main_window)


def update_disk_type_combobox(main_window):
    """
    Обновление ComboBox ch_disk_type из таблицы DiskType.
    """
    logger.info("Обновление ComboBox 'Тип диска'")
    session = Session()
    try:
        disk_types = session.query(DiskType).all()
        logger.info(f"Загружено {len(disk_types)} типов дисков из базы данных")

        # Очищаем ComboBox
        main_window.ch_disk_type.clear()
        main_window.ch_measurements.clear()

        # Заполняем ComboBox типами дисков
        for disk_type in disk_types:
            logger.info(f"Добавление в ComboBox: {disk_type.name} (ID: {disk_type.id})")
            main_window.ch_disk_type.addItem(disk_type.name, disk_type.id)
    except Exception as e:
        logger.error(f"Ошибка при обновлении ComboBox 'Тип диска': {e}")
    finally:
        session.close()


def update_measurements(main_window):
    """
    Обновление ListView ch_measurements для выбранного типа диска.
    """
    selected_disk_type_id = main_window.ch_disk_type.currentData()  # Получаем ID выбранного типа диска
    logger.info(f"Выбран тип диска с ID: {selected_disk_type_id}")

    if selected_disk_type_id:
        session = Session()
        try:
            disk_scans = session.query(DiskScan).filter_by(disk_type_id=selected_disk_type_id).all()
            logger.info(f"Загружено {len(disk_scans)} измерений для типа диска с ID {selected_disk_type_id}")

            # Очищаем ListView
            main_window.ch_measurements.clear()

            # Заполняем ListView новыми измерениями
            for scan in disk_scans:
                item = QListWidgetItem(f"{scan.name} ({scan.created_at})")
                item.setData(Qt.UserRole, scan.id)  # Сохраняем ID измерения в элементе ListView
                main_window.ch_measurements.addItem(item)
                logger.info(f"Добавлено измерение: {scan.name} (ID: {scan.id}, Дата: {scan.created_at})")
        except Exception as e:
            logger.error(f"Ошибка при обновлении измерений: {e}")
        finally:
            session.close()


def update_blade_results(main_window):
    """
    Обновление QTableWidget ch_blade_results для выбранного измерения.
    """
    selected_measurement_item = main_window.ch_measurements.currentItem()
    if selected_measurement_item:
        selected_scan_id = selected_measurement_item.data(Qt.UserRole)  # Получаем ID измерения
        logger.info(f"Обновление результатов для измерения с ID: {selected_scan_id}")

        session = Session()
        try:
            blades = session.query(Blade).filter_by(disk_scan_id=selected_scan_id).all()
            logger.info(f"Загружено {len(blades)} лопаток для измерения с ID {selected_scan_id}")

            # Очищаем QTableWidget перед заполнением новыми данными
            main_window.ch_blade_results.clearContents()
            main_window.ch_blade_results.setRowCount(len(blades))  # Устанавливаем количество строк

            # Устанавливаем заголовки столбцов
            main_window.ch_blade_results.setColumnCount(3)
            main_window.ch_blade_results.setHorizontalHeaderLabels(["Номер лопатки", "Скан", "Дефект"])

            # Заполняем таблицу данными о лопатках
            for row, blade in enumerate(blades):
                main_window.ch_blade_results.setItem(row, 0, QTableWidgetItem(str(blade.num)))
                main_window.ch_blade_results.setItem(row, 1, QTableWidgetItem(blade.scan))
                prediction = "Да" if blade.prediction else "Нет"
                main_window.ch_blade_results.setItem(row, 2, QTableWidgetItem(prediction))
                logger.info(f"Лопатка {blade.num}: Скан: {blade.scan}, Дефект: {prediction}")

            # Автоматическая подгонка размера столбцов и строк по содержимому
            main_window.ch_blade_results.resizeColumnsToContents()
            main_window.ch_blade_results.resizeRowsToContents()

            # Растягивание столбцов для заполнения пространства
            header = main_window.ch_blade_results.horizontalHeader()
            header.setSectionResizeMode(QHeaderView.Stretch)
        except Exception as e:
            logger.error(f"Ошибка при обновлении результатов для измерения: {e}")
        finally:
            session.close()