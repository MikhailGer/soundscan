import logging
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QListWidgetItem, QTableWidgetItem, QHeaderView, QWidget

from src.db import Session
from src.models import DiskType, DiskScan, Blade

# Настройка логгера для модуля
logger = logging.getLogger(__name__)

class ChangeHistoryTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.signals_connected = False

    def connect_signals(self):
        #Подключаем события
        if not self.signals_connected:
            # Привязываем события
            self._set_signal_state(True)
            self.signals_connected = True

        logger.info("Настройка вкладки 'История измерений' завершена, сигналы включены")

    def disconnect_signals(self):
        #Подключаем события
        if self.signals_connected:
            self._set_signal_state(False)
            self.signals_connected = False
            self.clear_fields()

            logger.info("'История измерений', сигналы отключены")

    def start_tab(self):
        logger.info("вкладка 'История измерений': отрисовка")
        self.update_disk_type_combobox()

    def _set_signal_state(self, connect: bool): #сделано для того чтобы в будущем было проще добавлять кнопки
        """
        Подключает или отключает сигналы для вкладки 'Типы дисков'. :param connect: True для подключения сигналов, False для отключения.
        """
        method = self.main_window.ch_disk_type.currentIndexChanged.connect if connect else self.main_window.ch_disk_type.currentIndexChanged.disconnect
        method(self.update_measurements)
        method = self.main_window.ch_measurements.itemSelectionChanged.connect if connect else self.main_window.ch_measurements.itemSelectionChanged.disconnect
        method(self.update_blade_results)


    def update_disk_type_combobox(self):
        """
        Обновление ComboBox ch_disk_type из таблицы DiskType.
        """
        logger.info("Обновление ComboBox 'Тип диска'")
        session = Session()
        try:
            disk_types = session.query(DiskType).all()
            logger.info(f"Загружено {len(disk_types)} типов дисков из базы данных")

            # Очищаем ComboBox
            self.main_window.ch_disk_type.clear()
            self.main_window.ch_measurements.clear()

            # Заполняем ComboBox типами дисков
            for disk_type in disk_types:
                logger.info(f"Добавление в ComboBox: {disk_type.name} (ID: {disk_type.id})")
                self.main_window.ch_disk_type.addItem(disk_type.name, disk_type.id)
        except Exception as e:
            logger.error(f"Ошибка при обновлении ComboBox 'Тип диска': {e}")
        finally:
            session.close()


    def update_measurements(self):
        """
        Обновление ListView ch_measurements для выбранного типа диска.
        """
        selected_disk_type_id = self.main_window.ch_disk_type.currentData()  # Получаем ID выбранного типа диска
        logger.info(f"Выбран тип диска с ID: {selected_disk_type_id}")

        if selected_disk_type_id:
            session = Session()
            try:
                disk_scans = session.query(DiskScan).filter_by(disk_type_id=selected_disk_type_id).all()
                logger.info(f"Загружено {len(disk_scans)} измерений для типа диска с ID {selected_disk_type_id}")

                # Очищаем ListView
                self.main_window.ch_measurements.clear()

                # Заполняем ListView новыми измерениями
                for scan in disk_scans:
                    item = QListWidgetItem(f"{scan.name} ({scan.created_at})")
                    item.setData(Qt.UserRole, scan.id)  # Сохраняем ID измерения в элементе ListView
                    self.main_window.ch_measurements.addItem(item)
                    logger.info(f"Добавлено измерение: {scan.name} (ID: {scan.id}, Дата: {scan.created_at})")
            except Exception as e:
                logger.error(f"Ошибка при обновлении измерений: {e}")
            finally:
                session.close()


    def update_blade_results(self):
        """
        Обновление QTableWidget ch_blade_results для выбранного измерения.
        """
        self.main_window.ch_blade_results.clear()
        self.main_window.ch_blade_results.setRowCount(0)

        selected_measurement_item = self.main_window.ch_measurements.currentItem()
        if selected_measurement_item:
            selected_scan_id = selected_measurement_item.data(Qt.UserRole)  # Получаем ID измерения
            logger.info(f"Обновление результатов для измерения с ID: {selected_scan_id}")

            session = Session()
            try:
                blades = session.query(Blade).filter_by(disk_scan_id=selected_scan_id).all()
                logger.info(f"Загружено {len(blades)} лопаток для измерения с ID {selected_scan_id}")

                # Очищаем QTableWidget перед заполнением новыми данными
                self.main_window.ch_blade_results.clearContents()
                self.main_window.ch_blade_results.setRowCount(len(blades))  # Устанавливаем количество строк

                # Устанавливаем заголовки столбцов
                self.main_window.ch_blade_results.setColumnCount(2)
                self.main_window.ch_blade_results.setHorizontalHeaderLabels(["Номер лопатки", "Дефект"])

                # Заполняем таблицу данными о лопатках
                for row, blade in enumerate(blades):
                    self.main_window.ch_blade_results.setItem(row, 0, QTableWidgetItem(str(blade.num)))
                    # self.main_window.ch_blade_results.setItem(row, 1, QTableWidgetItem(blade.scan)) скан загружать не будем, потому что это звук
                    prediction = "Нет дефекта" if blade.prediction else "Дефект"
                    self.main_window.ch_blade_results.setItem(row, 1, QTableWidgetItem(prediction))
                    logger.info(f"Лопатка {blade.num}:, Дефект: {prediction}")

                # Автоматическая подгонка размера столбцов и строк по содержимому
                self.main_window.ch_blade_results.resizeColumnsToContents()
                self.main_window.ch_blade_results.resizeRowsToContents()

                # Растягивание столбцов для заполнения пространства
                header = self.main_window.ch_blade_results.horizontalHeader()
                header.setSectionResizeMode(QHeaderView.Stretch)
            except Exception as e:
                logger.error(f"Ошибка при обновлении результатов для измерения: {e}")
            finally:
                session.close()

    def clear_fields(self):
        self.main_window.ch_blade_results.clearSelection()
        self.main_window.ch_blade_results.clear()
        self.main_window.ch_blade_results.setCurrentItem(None)

        self.main_window.ch_measurements.clearSelection()
        self.main_window.ch_measurements.clear()
        self.main_window.ch_measurements.setCurrentItem(None)

        self.main_window.ch_disk_type.clear()
        self.main_window.ch_blade_results.setRowCount(0)
        logger.info("Поля очищены(ChangeHistory)")