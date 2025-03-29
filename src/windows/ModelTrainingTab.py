import logging
from functools import partial
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QListWidgetItem, QCheckBox, QWidget, QHBoxLayout, QTableWidgetItem, QHeaderView, QPushButton
from src.db import Session
from src.models import DiskType, DiskScan, Blade

# Настройка логирования
logger = logging.getLogger(__name__)


class ModelTrainingTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.signals_connected = False

    def _set_signal_state(self, connect: bool): #сделано для того чтобы в будущем было проще добавлять кнопки
        """
        Подключает или отключает сигналы для вкладки 'Типы дисков'. :param connect: True для подключения сигналов, False для отключения.
        """
        method = self.main_window.mt_disk_type.currentIndexChanged.connect if connect else self.main_window.mt_disk_type.currentIndexChanged.disconnect
        method(self.update_measurements)
        method = self.main_window.mt_measurements.itemSelectionChanged.connect if connect else self.main_window.mt_measurements.itemSelectionChanged.connect
        method(self.update_blade_results)

    def connect_signals(self):
        #Подключаем события
        if not self.signals_connected:
            self._set_signal_state(True)
            self.signals_connected = True

        logger.info("Настройка вкладки 'Обучение ИИ' завершена, сигналы включены")

    def disconnect_signals(self):
        #Подключаем события
        if self.signals_connected:
            self._set_signal_state(False)
            self.signals_connected = False

            logger.info("'Обучение ИИ', сигналы отключены")

    def start_tab(self):
        logger.info("вкладка 'Обучение ИИ': отрисовка")
        self.update_disk_type_combobox()


    def update_disk_type_combobox(self):
        """
        Обновление ComboBox mt_disk_type из таблицы DiskType.
        """
        logger.info("Обновление ComboBox с типами дисков")
        session = Session()
        try:
            disk_types = session.query(DiskType).all()
            logger.info(f"Загружено {len(disk_types)} типов дисков")

            # Очищаем ComboBox и связанные элементы
            self.main_window.mt_disk_type.clear()
            self.main_window.mt_measurements.clear()
            self.main_window.mt_blade_results.clearContents()

            # Заполняем ComboBox типами дисков
            for disk_type in disk_types:
                self.main_window.mt_disk_type.addItem(disk_type.name, disk_type.id)
        except Exception as e:
            logger.error(f"Ошибка при загрузке типов дисков: {e}")
        finally:
            session.close()


    def update_measurements(self):
        """
        Обновление ListWidget mt_measurements для выбранного типа диска.
        Добавление чекбоксов для изменения поля is_training.
        """
        selected_disk_type_id = self.main_window.mt_disk_type.currentData()  # Получаем ID выбранного типа диска
        logger.info(f"Обновление измерений для типа диска с ID {selected_disk_type_id}")

        if selected_disk_type_id:
            session = Session()
            try:
                disk_scans = session.query(DiskScan).order_by(DiskScan.id.asc()).all()
                logger.info(f"Загружено {len(disk_scans)} измерений для типа диска ID {selected_disk_type_id}")

                # Очищаем ListWidget
                self.main_window.mt_measurements.clear()

                # Заполняем ListWidget новыми измерениями и добавляем чекбоксы
                for scan in disk_scans:
                    item = QListWidgetItem(self.main_window.mt_measurements)
                    item.setText(scan.name)
                    item.setData(Qt.UserRole, scan.id)  # Сохраняем ID измерения

                    # Создаем виджет для чекбокса
                    widget = QWidget()
                    checkbox = QCheckBox()
                    checkbox.setChecked(scan.is_training)  # Устанавливаем текущее состояние is_training
                    checkbox.setStyleSheet("""
                        QCheckBox::indicator {
                            width: 25px;
                            height: 25px;
                        }
                        QCheckBox {
                            font-size: 18px;
                        }
                    """)
                    # Создаем layout для размещения чекбокса справа
                    layout = QHBoxLayout(widget)
                    layout.addWidget(checkbox)
                    layout.setAlignment(Qt.AlignRight)  # Перемещаем чекбокс вправо
                    layout.setContentsMargins(0, 0, 50, 0)  # отступы
                    widget.setLayout(layout)

                    self.main_window.mt_measurements.setItemWidget(item, widget)
                    checkbox.stateChanged.connect(partial(self.change_is_training_state, scan.id))
            except Exception as e:
                logger.error(f"Ошибка при обновлении измерений для типа диска ID {selected_disk_type_id}: {e}")
            finally:
                session.close()


    def change_is_training_state(self, scan_id, state):
        """
        Обновление поля is_training для выбранного измерения в базе данных при изменении состояния QCheckBox.
        """
        logger.info(f"Изменение состояния is_training для измерения ID {scan_id} на {state}")
        session = Session()
        try:
            scan = session.query(DiskScan).get(scan_id)
            if scan:
                scan.is_training = (state == Qt.Checked)
                session.commit()
                logger.info(f"Состояние is_training для измерения ID {scan_id} обновлено на {scan.is_training}")
        except Exception as e:
            logger.error(f"Ошибка при изменении состояния is_training для измерения ID {scan_id}: {e}")
        finally:
            session.close()


    def update_blade_results(self):
        """
        Обновление QTableWidget mt_blade_results для выбранного измерения.
        """
        self.main_window.mt_blade_results.clear()
        self.main_window.mt_blade_results.setRowCount(0)

        selected_measurement_item = self.main_window.mt_measurements.currentItem()
        if selected_measurement_item:
            selected_scan_id = selected_measurement_item.data(Qt.UserRole)  # Получаем ID измерения
            logger.info(f"Обновление результатов для измерения ID {selected_scan_id}")

            session = Session()
            try:
                blades = session.query(Blade).filter_by(disk_scan_id=selected_scan_id).order_by(Blade.num.asc()).all()
                logger.info(f"Загружено {len(blades)} лопаток для измерения ID {selected_scan_id}")

                self.main_window.mt_blade_results.clearContents()
                self.main_window.mt_blade_results.setRowCount(len(blades))  # Устанавливаем количество строк
                self.main_window.mt_blade_results.setColumnCount(3)
                self.main_window.mt_blade_results.setHorizontalHeaderLabels(["Номер лопатки", "Дефект", "Ручное управление статусом"])
                self.main_window.mt_blade_results.horizontalHeader().setVisible(True)

                for row, blade in enumerate(blades):
                    self.main_window.mt_blade_results.setItem(row, 0, QTableWidgetItem(str(blade.num)))
                    prediction = (
                        "Годен" if blade.prediction is True else
                        "Не годен" if blade.prediction is False else
                        "Не оценено"
                    )
                    self.main_window.mt_blade_results.setItem(row, 1, QTableWidgetItem(prediction))
                    logger.info(f"Лопатка {blade.num}:, Дефект: {prediction}")

                    btn_no_defect = QPushButton("Нет дефекта")
                    btn_no_defect.clicked.connect(lambda _, b=blade: self.set_blade_defect_status(b.id,True))
                    btn_no_defect.setStyleSheet("background-color: lightgreen;")

                    btn_defect = QPushButton("Дефект")
                    btn_defect.clicked.connect(lambda _, b=blade: self.set_blade_defect_status(b.id, False))
                    btn_defect.setStyleSheet("background-color: red; color: white;")

                    btn_no_data = QPushButton("Нет данных")
                    btn_no_data.clicked.connect(lambda _, b=blade: self.set_blade_defect_status(b.id, None))



                    widget = QWidget()
                    layout = QHBoxLayout()
                    layout.addWidget(btn_defect)
                    layout.addWidget(btn_no_defect)
                    layout.addWidget(btn_no_data)
                    layout.setContentsMargins(0,0,0,0)
                    widget.setLayout(layout)

                    self.main_window.mt_blade_results.setCellWidget(row, 2, widget)

                # self.main_window.mt_blade_results.resizeColumnsToContents()
                # self.main_window.mt_blade_results.resizeRowsToContents()

                header = self.main_window.mt_blade_results.horizontalHeader()
                for i in range(self.main_window.mt_blade_results.columnCount()):
                    header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
            except Exception as e:
                logger.error(f"Ошибка при обновлении результатов для измерения ID {selected_scan_id}: {e}")
            finally:
                session.close()

    def set_blade_defect_status(self, blade_id, status):
        """Обновляет статус дефекта лопатки по нажатию"""
        logger.info(f"Изменение статуса дефекта лопатки ID {blade_id} на {status}")
        session = Session()
        try:
            blade = session.query(Blade).get(blade_id)
            if blade:
                blade.prediction = status
                session.commit()
                logger.info(f"Статус дефекта лопатки ID {blade_id} изменен на {status}")
                self.update_blade_results()
        except Exception as e:
            logger.error(f"Ошибка при изменении статуса дефекта лопатки ID {Blade}: {e}")
        finally:
            session.close()

