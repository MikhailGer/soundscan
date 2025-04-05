import logging
from itertools import repeat
from multiprocessing.managers import Value

from PyQt5.QtWidgets import QHeaderView, QWidget, QDialog, QBoxLayout, QLabel, QLineEdit, QCheckBox, QPushButton, \
    QVBoxLayout, QMessageBox
from PyQt5.QtWidgets import QTableWidgetItem, QTabBar, QTabWidget
from PyQt5.QtCore import QMetaObject, Qt, QThread, QLine, pyqtSlot
from PyQt5.QtGui import QIntValidator
from sqlalchemy import values, Select

from src.db import Session
from src.models import DiskType, Blade, DiskScan

from src.scan.Scanning import Scanning

class SeriesScanDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Серийное сканирование")

        layout = QVBoxLayout()
        self.label = QLabel("Укажите количество сканирований:")
        self.line_editscans = QLineEdit()
        self.checkbox_infinite = QCheckBox("Бесконечное сканирование")

        self.line_editscans.setValidator(QIntValidator(1,99999, self.line_editscans))
        self.button_ok = QPushButton("Начать")
        self.button_cancel = QPushButton("Отмена")

        layout.addWidget(self.label)
        layout.addWidget(self.line_editscans)
        layout.addWidget(self.checkbox_infinite)
        layout.addWidget(self.button_ok)
        layout.addWidget(self.button_cancel)

        self.setLayout(layout)
        self.button_cancel.clicked.connect(self.reject)
        self.button_ok.clicked.connect(self.accept)

    def get_values(self):
        if self.checkbox_infinite.isChecked():
            return None
        else:
            try:
                value = int(self.line_editscans.text().strip())
                if not value or value <= 1:
                    QMessageBox.warning(self, "Ошибка", "Введите целое число больше 1")
                    self.reject()
                else:
                    return value
            except ValueError:
                return 0

#классы для блокировки интерфейса
class NonSwitchableTabBar(QTabBar):
    def mousePressEvent(self, event):
        pass

    def mouseReleaseEvent(self, event):
        pass

    def mouseMoveEvent(self, event):
        pass

    def mouseDoubleClickEvent(self, event):
        pass

    def wheelEvent(self, event):
        pass


class NonSwitchableTabWidget(QTabWidget):
    def keyPressEvent(self, event):
        pass
# Настройка логирования
logger = logging.getLogger(__name__)

# теперь on_tab_changed вызывается 1 раз при инициализации приложения и управляет вкладками

class NewMeasurementTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.signals_connected = False
        self.current_scan = None
        self.series_mode = False
        self.series_infinite = False
        self.series_count = 0
        self.series_stoped = False

        self.current_disk_type_blades = []
        self.current_disk_type_id = None

        header = self.main_window.nm_measurements.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)


    def _set_signal_state(self, connect: bool): #сделано для того чтобы в будущем было проще добавлять кнопки
        """
        Подключает или отключает сигналы для вкладки 'Типы дисков'. :param connect: True для подключения сигналов, False для отключения.
        """
        method = self.main_window.nm_start.clicked.connect if connect else self.main_window.nm_start.clicked.disconnect
        method(self.start_control)
        method = self.main_window.nm_stop.clicked.connect if connect else self.main_window.nm_stop.clicked.disconnect
        method(self.stop_control)
        method = self.main_window.nm_serial_scan.clicked.connect if connect else self.main_window.nm_serial_scan.clicked.disconnect
        method(self.on_series_scan_clicked)

    def connect_signals(self):
        #Подключаем события
        if not self.signals_connected:
            self._set_signal_state(True)
            self.signals_connected = True

        logger.info("Настройка вкладки 'Новое измерение' завершена, сигналы включены")

    def disconnect_signals(self):
        #Подключаем события
        if self.signals_connected:
            self._set_signal_state(False)
            self.signals_connected = False

            logger.info("'Новое измерение', сигналы отключены")


    def start_tab(self):
        logger.info("вкладка 'Новое измерение': отрисовка")
        self.load_disk_types_to_combobox()
        self.set_controls_enabled(True)

    def load_disk_types_to_combobox(self):
        """
        Загрузка типов дисков в nm_disk_type.
        """
        logger.info("Загрузка типов дисков в ComboBox")
        session = Session()
        try:
            disk_types = session.query(DiskType).all()
            logger.info(f"Загружено {len(disk_types)} типов дисков из базы данных")

            self.main_window.nm_disk_type.clear()
            for disk_type in disk_types:
                self.main_window.nm_disk_type.addItem(disk_type.name, disk_type.id)
                logger.debug(f"Добавлен тип диска: {disk_type.name} (ID: {disk_type.id})")
        except Exception as e:
            logger.error(f"Ошибка при загрузке типов дисков: {e}")
        finally:
            session.close()

    def set_controls_enabled(self, enabled):
        """
        Установка доступности элементов интерфейса.
        Если enabled = False, блокируются все элементы, кроме nm_stop.
        """
        logger.info(f"Установка доступности элементов интерфейса: {'Включены' if enabled else 'Отключены'}")
        # main_window.tabWidget.setEnabled(enabled) //блокирует все эллементы и не дает нажимать кнопки
        self.main_window.nm_start.setEnabled(enabled)
        self.main_window.nm_serial_scan.setEnabled(enabled)
        self.main_window.nm_disk_type.setEnabled(enabled)
        self.main_window.nm_measurements.setEnabled(enabled)
        print("кнопка stop is ")
        print(not enabled)
        self.main_window.nm_stop.setEnabled(not enabled)
        if not enabled:
            try:
                self.disable_tab_switching()
            except Exception as e:
                logger.error(f"Ошибка блокировки интерфейса: {e}")
        else:
            try:
                self.enable_tab_switching()
            except Exception as e:
                logger.error(f"Ошибка разблокировки интерфейса: {e}")


    def disable_tab_switching(self):
        self.main_window.tab_switching_enabled = False
        self.main_window.tabWidget.keyPressEvent = None
        logger.info("Переключение вкладок отключено")


    def enable_tab_switching(self):
        self.main_window.tab_switching_enabled = True
        self.main_window.tabWidget.keyPressEvent = super(QTabWidget, self.main_window.tabWidget).keyPressEvent
        logger.info("Переключение вкладок включено")

    def start_control(self):
        """
        Начало процесса контроля.
        """
        if not self.main_window.connection_established:
            logger.error("Не подключена плата.")
            QMessageBox.warning(self,"Ошибка", "Не подключена плата")
            return
        logger.info("Начало процесса контроля")
        selected_item = self.main_window.nm_disk_type.currentText()

        if not selected_item:
            logger.error("Не выбран тип диска для сканирования.")
            return

        try:
            # Используем контекстный менеджер для автоматического закрытия сессии
            with Session() as session:
                # Получаем тип диска из базы данных по имени
                disk_type = session.query(DiskType).filter_by(name=selected_item).first()
                if not disk_type:
                    logger.error(f"Тип диска с именем '{selected_item}' не найден.")
                    return
                logger.info(f"Запуск сканирования диска с ID {disk_type.id}")
                self.set_controls_enabled(False)  # Блокируем элементы
                # Запуск контроля на Arduino
                logger.info("Отправка команды на старт контроля")
                self.current_scan = Scanning(disk_type.id, self.main_window.arduino_worker)
                self.scanning_thread = QThread()
                self.current_scan.moveToThread(self.scanning_thread)
                self.scanning_thread.started.connect(self.current_scan.start_scan)
                self.current_scan.blade_downloaded.connect(self.on_blade_downloaded)
                self.current_scan.scanning_finished.connect(self.scanning_thread.quit)
                self.current_scan.scanning_finished.connect(self.on_scanning_finished)
                self.current_scan.scanning_finished.connect(self.scanning_thread.deleteLater)
                # self.current_scan.scanning_finished.connect(self.scanning_thread.deleteLater) убрал 8.03.25
                self.scanning_thread.start()


        except Exception as e:
            logger.error(f"Ошибка при старте сканирования: {e}", exc_info=True)

    def stop_control(self):
        """
        Остановка процесса контроля.
        """
        if not self.current_scan:
            logger.info("Процесс контроля еще не был начат")
            return
        logger.info("Остановка процесса контроля")
        self.series_stoped = True
        # main_window.current_scan.stop()
        QMetaObject.invokeMethod(self.current_scan, 'stop_scan', Qt.QueuedConnection)

    def on_series_scan_clicked(self):
        if not self.main_window.connection_established:
            logger.error("Не подключена плата.")
            QMessageBox.warning(self,"Ошибка", "Не подключена плата")
            return
        dialog = SeriesScanDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            repeats = dialog.get_values()
            if repeats is None:
                logger.info("Начать бесконечное сканирование")
                self.start_series_scan(infinite=True)
            else:
                logger.info(f"Начать сканирование {repeats} раз")
                self.start_series_scan(repeats=repeats)


    def start_series_scan(self, infinite = False, repeats=1):
        self.series_mode = True
        self.series_stoped = False
        self.series_infinite = infinite
        self.series_count = repeats if not infinite else float('inf')
        logger.info("Начинается серийное сканирование")
        self.start_control()


    def on_scanning_finished(self):
        if self.series_mode and not self.series_stoped:
            logger.info("Серийное сканирование: одна из итераций завершилась")
            if self.series_infinite or self.series_count > 1:
                if not self.series_infinite:
                    self.series_count -= 1
                    logger.info(f"Серийное сканирование: осталось {self.series_count} итераций")
                self.start_control()
                return
            else:
                self.series_mode = False

        self.set_controls_enabled(True)  # Разблокируем элементы
        logger.info("Контроль завершен и элементы интерфейса разблокированы")
        self.update_blade_fields()
        self.current_scan = None
        self.scanning_thread = None


    def add_blade(self):
        print("пока пусто")

    def update_blade_fields(self):
        self.main_window.nm_measurements.clear()
        selected_item = self.main_window.nm_disk_type.currentText()

        self.main_window.nm_measurements.setRowCount(0)
        self.main_window.nm_measurements.setColumnCount(3)
        self.main_window.nm_measurements.setHorizontalHeaderLabels(["№ DiskScan", "№ Лопатки", "Результат"])

        if not selected_item:
            logger.error("Не выбран тип диска для сканирования.")
            return

        with Session() as session:
            # Получаем DiskType по имени
            disk_type = session.query(DiskType).filter_by(name=selected_item).first()

            if not disk_type:
                logger.error(f"DiskType с именем '{selected_item}' не найден.")
                return

            try:
                # Получаем все DiskScan для этого DiskType
                disk_scans = session.query(DiskScan).filter_by(disk_type_id=disk_type.id).all()

                if not disk_scans:
                    logger.error(f"Для DiskType с id {disk_type.id} нет доступных DiskScan.")
                    return

                # Собираем все id DiskScan
                disk_scan_ids = [ds.id for ds in disk_scans]

                # Получаем Blade, связанные с этими DiskScan
                blades = session.query(Blade).filter(Blade.disk_scan_id.in_(disk_scan_ids)).order_by(Blade.disk_scan_id, Blade.num).all()

                self.current_disk_type_blades = blades
                self.current_disk_type_id = disk_type.id

                logger.info(f"Загружено {len(blades)} лопаток для DiskType с id {disk_type.id}.")

                # Заполнение таблицы измерений
                self.main_window.nm_measurements.setRowCount(len(blades))
                self.main_window.nm_measurements.setColumnCount(3)
                self.main_window.nm_measurements.setHorizontalHeaderLabels(["№ DiskScan", "№ Лопатки", "Результат"])


                for row, blade in enumerate(blades):
                    # Номер DiskScan
                    self.main_window.nm_measurements.setItem(row, 0, QTableWidgetItem(str(blade.disk_scan_id)))
                    # Номер лопатки
                    self.main_window.nm_measurements.setItem(row, 1, QTableWidgetItem(str(blade.num)))
                    # Результат
                    # result = "Годен" if blade.prediction else "Не годен"
                    result = (
                        "Годен" if blade.prediction is True else
                        "Не годен" if blade.prediction is False else
                        "Не оценено"
                    )
                    self.main_window.nm_measurements.setItem(row, 2, QTableWidgetItem(result))
                    logger.debug(f"DiskScan {blade.disk_scan_id}, Лопатка {blade.num}: {result}")
            except Exception as e:
                logger.error(f"Ошибка при обновлении данных лопаток: {e}", exc_info=True)

    @pyqtSlot(object)
    def on_blade_downloaded(self, blade):
        if blade.disk_type_id == self.current_disk_type_id:
            self.current_disk_type_blades.append(blade)
            self.add_blade_to_table(blade)

    def add_blade_to_table(self, blade):
        table = self.main_window.nm_measurements
        row_count = table.rowCount()
        table.insertRow(row_count)

        table.setItem(row_count, 0, QTableWidgetItem(str(blade.disk_scan_id)))
        table.setItem(row_count, 1, QTableWidgetItem(str(blade.num)))
        result = (
            "Годен" if blade.prediction is True else
            "Не годен" if blade.prediction is False else
            "Не оценено"
        )
        table.setItem(row_count, 2, QTableWidgetItem(result))

        table.scrollToItem(table.item(row_count, 0))






