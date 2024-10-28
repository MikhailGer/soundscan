import logging
from operator import index
from PyQt5.QtWidgets import QHeaderView
from PyQt5.QtSerialPort import QSerialPort
from PyQt5.QtWidgets import QTableWidgetItem, QTabBar, QTabWidget
from PyQt5.QtCore import QMetaObject, Qt, QThread
from src.db import Session
from src.models import DiskType, Blade, DiskScan

from Scanning import Scanning

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
    # main_window.tabWidget.setEnabled(enabled) //блокирует все эллементы и не дает нажимать кнопки
    main_window.nm_start.setEnabled(enabled)
    main_window.nm_disk_type.setEnabled(enabled)
    main_window.nm_measurements.setEnabled(enabled)
    main_window.nm_stop.setEnabled(not enabled)
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


def disable_tab_switching(main_window):
    main_window.tab_switching_enabled = False
    main_window.tabWidget.keyPressEvent = lambda event: None
    logger.info("Переключение вкладок отключено")


def enable_tab_switching(main_window):
    main_window.tab_switching_enabled = True
    main_window.tabWidget.keyPressEvent = super(QTabWidget, main_window.tabWidget).keyPressEvent
    logger.info("Переключение вкладок включено")

def start_control(main_window):
    """
    Начало процесса контроля.
    """
    if main_window.connection_established:
        logger.info("Начало процесса контроля")
        selected_item = main_window.nm_disk_type.currentText()

        if selected_item:
            try:
                # Используем контекстный менеджер для автоматического закрытия сессии
                with Session() as session:
                    # Получаем тип диска из базы данных по имени
                    disk_type = session.query(DiskType).filter_by(name=selected_item).first()
                    if disk_type:
                        logger.info(f"Запуск сканирования диска с ID {disk_type.id}")
                        set_controls_enabled(main_window, False)  # Блокируем элементы
                        # Запуск контроля на Arduino
                        logger.info("Отправка команды на старт контроля")
                        #todo переделать логику старта сканирования

                        # main_window.current_scan = Scanning(disk_type.id, main_window.arduino_worker)
                        # main_window.current_scan.start_scan()
                        # main_window.current_scan.scanning_finished.connect(lambda: stop_control(main_window))
                        main_window.current_scan = Scanning(disk_type.id, main_window.arduino_worker)
                        main_window.scanning_thread = QThread()
                        main_window.current_scan.moveToThread(main_window.scanning_thread)
                        main_window.scanning_thread.started.connect(main_window.current_scan.start_scan)
                        main_window.current_scan.blade_downloaded.connect(lambda: update_blade_fields(main_window))
                        main_window.current_scan.scanning_finished.connect(main_window.scanning_thread.quit)
                        main_window.current_scan.scanning_finished.connect(main_window.scanning_thread.deleteLater)
                        main_window.current_scan.scanning_finished.connect(main_window.scanning_thread.deleteLater)
                        main_window.scanning_thread.start()
                    else:
                        logger.error(f"Тип диска с именем '{selected_item}' не найден.")

            except Exception as e:
                logger.error(f"Ошибка при старте сканирования: {e}", exc_info=True)

        else:
            logger.error("Не выбран тип диска для сканирования.")
    else:
        logger.error("Не подключена плата.")

def stop_control(main_window):
    """
    Остановка процесса контроля.
    """
    logger.info("Остановка процесса контроля")
    # main_window.current_scan.stop()
    QMetaObject.invokeMethod(main_window.current_scan, 'stop_scan', Qt.QueuedConnection)
    # arduino.stop_mode()  # Остановка контроля на Arduino
    set_controls_enabled(main_window, True)  # Разблокируем элементы
    logger.info("Контроль завершен и элементы интерфейса разблокированы")
    update_blade_fields(main_window)


def update_blade_fields(main_window):
    main_window.nm_measurements.clear()
    selected_item = main_window.nm_disk_type.currentText()

    if selected_item:
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
                blades = session.query(Blade).filter(Blade.disk_scan_id.in_(disk_scan_ids)).all()

                logger.info(f"Загружено {len(blades)} лопаток для DiskType с id {disk_type.id}.")

                # Заполнение таблицы измерений
                main_window.nm_measurements.setRowCount(len(blades))
                main_window.nm_measurements.setColumnCount(3)
                main_window.nm_measurements.setHorizontalHeaderLabels(["№ DiskScan", "№ Лопатки", "Результат"])
                header = main_window.nm_measurements.horizontalHeader()
                header.setSectionResizeMode(QHeaderView.Stretch)

                for row, blade in enumerate(blades):
                    # Номер DiskScan
                    main_window.nm_measurements.setItem(row, 0, QTableWidgetItem(str(blade.disk_scan_id)))
                    # Номер лопатки
                    main_window.nm_measurements.setItem(row, 1, QTableWidgetItem(str(blade.num)))
                    # Результат
                    result = "Годен" if blade.prediction else "Не годен"
                    main_window.nm_measurements.setItem(row, 2, QTableWidgetItem(result))
                    logger.debug(f"DiskScan {blade.disk_scan_id}, Лопатка {blade.num}: {result}")
            except Exception as e:
                logger.error(f"Ошибка при обновлении данных лопаток: {e}", exc_info=True)
    else:
        logger.error("Не выбран тип диска для сканирования.")


def setup_new_measurement_tab(main_window):
    """
    Настройка логики вкладки "Новое измерение".
    """
    logger.info("Настройка вкладки 'Новое измерение'")
    main_window.nm_start.clicked.connect(lambda: start_control(main_window))
    main_window.nm_stop.clicked.connect(lambda: stop_control(main_window))

