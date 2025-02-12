import logging
from PyQt5.QtWidgets import QHeaderView, QWidget
from PyQt5.QtWidgets import QTableWidgetItem, QTabBar, QTabWidget
from PyQt5.QtCore import QMetaObject, Qt, QThread
from src.db import Session
from src.models import DiskType, Blade, DiskScan

from src.scan.Scanning import Scanning

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
        self.main_window.nm_disk_type.setEnabled(enabled)
        self.main_window.nm_measurements.setEnabled(enabled)
        self.main_window.nm_stop.setEnabled(not enabled)
        if not enabled:
            try:
                disable_tab_switching(main_window)
            except Exception as e:
                logger.error(f"Ошибка блокировки интерфейса: {e}")
        else:
            try:
                enable_tab_switching(main_window)
            except Exception as e:
                logger.error(f"Ошибка разблокировки интерфейса: {e}")


    def disable_tab_switching(self):
        self.main_window.tab_switching_enabled = False
        self.main_window.tabWidget.keyPressEvent = None
        logger.info("Переключение вкладок отключено")


    def enable_tab_switching(self):
        self.main_window.tab_switching_enabled = True
        self.main_window.tabWidget.keyPressEvent = super(QTabWidget, main_window.tabWidget).keyPressEvent
        logger.info("Переключение вкладок включено")

    def start_control(self):
        """
        Начало процесса контроля.
        """
        if not self.main_window.connection_established:
            logger.error("Не подключена плата.")
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
                self.current_scan.blade_downloaded.connect(self.update_blade_fields)
                self.current_scan.scanning_finished.connect(self.scanning_thread.quit)
                self.current_scan.scanning_finished.connect(self.scanning_thread.deleteLater)
                self.current_scan.scanning_finished.connect(self.scanning_thread.deleteLater)
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
        # main_window.current_scan.stop()
        QMetaObject.invokeMethod(self.current_scan, 'stop_scan', Qt.QueuedConnection)
        # arduino.stop_mode()  # Остановка контроля на Arduino
        set_controls_enabled(True)  # Разблокируем элементы
        logger.info("Контроль завершен и элементы интерфейса разблокированы")
        update_blade_fields(self.main_window)
        self.current_scan = None


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
                    result = "Годен" if blade.prediction else "Не годен"
                    self.main_window.nm_measurements.setItem(row, 2, QTableWidgetItem(result))
                    logger.debug(f"DiskScan {blade.disk_scan_id}, Лопатка {blade.num}: {result}")
            except Exception as e:
                logger.error(f"Ошибка при обновлении данных лопаток: {e}", exc_info=True)




