import logging
import tempfile

import numpy as np
import io
import base64
import h5py
from functools import partial
from xml.sax.handler import feature_external_ges

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QListWidgetItem, QCheckBox, QWidget, QHBoxLayout, QTableWidgetItem, QHeaderView, QPushButton
from PyQt5.QtWidgets import QTableWidgetItem, QTabBar, QTabWidget, QApplication, QMessageBox

from pydantic_core.core_schema import model_field
from requests import session
from sqlalchemy import BLANK_SCHEMA, false
from tensorflow.python.keras.utils.version_utils import training

from src.db import Session
from src.models import DiskType, DiskScan, Blade, DiskTypeModel
from src.scan.ml_predict import extract_features, build_model

# Настройка логирования
logger = logging.getLogger(__name__)

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
        method(self.update_avaliable_models)
        method = self.main_window.mt_measurements.itemSelectionChanged.connect if connect else self.main_window.mt_measurements.itemSelectionChanged.connect
        method(self.update_blade_results)
        method = self.main_window.mt_save.clicked.connect if connect else self.main_window.mt_save.clicked.disconnect
        method(self.train_model)

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

    def set_controls_enabled(self, enabled):
        """
        Установка доступности элементов интерфейса.
        Если enabled = False, блокируются все элементы, кроме nm_stop.
        """
        logger.info(f"Установка доступности элементов интерфейса: {'Включены' if enabled else 'Отключены'}")
        # main_window.tabWidget.setEnabled(enabled) //блокирует все эллементы и не дает нажимать кнопки
        self.main_window.mt_disk_type.setEnabled(enabled)
        self.main_window.mt_save.setEnabled(enabled)
        self.main_window.mt_measurements.setEnabled(enabled)
        self.main_window.mt_blade_results.setEnabled(enabled)
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
                disk_scans = session.query(DiskScan).filter_by(disk_type_id=selected_disk_type_id).order_by(DiskScan.id.asc()).all()
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

    def update_avaliable_models(self):
        selected_disk_type_id = self.main_window.mt_disk_type.currentData()  # Получаем ID выбранного типа диска
        logger.info(f"Обновление моделей для типа диска с ID {selected_disk_type_id}")

        if selected_disk_type_id:
            session = Session()
            try:
                disk_models = session.query(DiskTypeModel).filter_by(disk_type_id=selected_disk_type_id).order_by(DiskTypeModel.id.asc()).all()
                logger.info(f"Загружено {len(disk_models)} измерений для типа диска ID {selected_disk_type_id}")

                # Очищаем ListWidget
                self.main_window.mt_avaliable_models.clear()

                # Заполняем ListWidget новыми измерениями и добавляем чекбоксы
                for model in disk_models:
                    item = QListWidgetItem(self.main_window.mt_avaliable_models)
                    item.setText(f"ID: {model.id} created_at:{model.created_at}")
                    item.setData(Qt.UserRole, model.id)  # Сохраняем ID измерения

                    # Создаем виджет для чекбокса
                    widget = QWidget()
                    checkbox = QCheckBox()
                    checkbox.setChecked(model.is_current)  # Устанавливаем текущее состояние is_training
                    checkbox.setStyleSheet("""
                                QCheckBox::indicator {
                                    width: 25px;
                                    height: 25px;
                                }
                                QCheckBox {
                                    font-size: 18px;
                                }
                            """)
                    delete_button = QPushButton("Удалить")
                    delete_button.setStyleSheet("background-color: red; color: white;")
                    delete_button.clicked.connect(partial(self.delete_model, model.id))
                    # Создаем layout для размещения чекбокса справа
                    layout = QHBoxLayout(widget)
                    layout.addWidget(checkbox)
                    layout.addWidget(delete_button)
                    layout.setAlignment(Qt.AlignRight)  # Перемещаем чекбокс вправо
                    layout.setContentsMargins(0, 0, 50, 0)  # отступы
                    widget.setLayout(layout)

                    self.main_window.mt_avaliable_models.setItemWidget(item, widget)
                    checkbox.stateChanged.connect(partial(self.change_is_current_state, model.id))
            except Exception as e:
                logger.error(f"Ошибка при обновлении измерений для типа диска ID {selected_disk_type_id}: {e}")
            finally:
                session.close()

    def delete_model(self, model_id):
        reply = QMessageBox.question(
            self,
             "Удалить модель",
            "Вы уверены, что хотите удалить эту обученную модель?",
             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
             QMessageBox.StandardButton.No
             )
        if reply == QMessageBox.Yes:
            session = Session()
            try:
                model = session.query(DiskTypeModel).get(model_id)
                if model:
                    session.delete(model)
                    session.commit()
                    logger.info(f"Модель {model_id} была удалена из базы данных.")
                else:
                    logger.info(f"Модель {model_id} не найдена.")
            except Exception as e:
                logger.error(f"Ошибка при удалении модели ID {model.id} из БД: {e}")

            finally:
                session.close()
        self.update_avaliable_models()

    def change_is_current_state(self, dt_model_id, state):
        logger.info(f"Изменение состояния is_current для модели ID {dt_model_id} на {state}")
        session = Session()
        try:
            model = session.query(DiskTypeModel).get(dt_model_id)
            if model:
                if state == Qt.Checked:
                    session.query(DiskTypeModel).filter (DiskTypeModel.disk_type_id == model.disk_type_id).update({DiskTypeModel.is_current: False})
                    model.is_current = True
                    # session.commit()
                    logger.info(f"Состояние is_current для модели ID {dt_model_id} обновлено на {model.is_current}")
                else:
                    model.is_current = False
                    logger.info(f"Состояние is_current для модели ID {dt_model_id} обновлено на {model.is_current}")
                session.commit()
        except Exception as e:

            logger.error(f"Ошибка при изменении состояния is_current для модели ID {dt_model_id}: {e}")
        finally:
            session.close()
            self.update_avaliable_models()

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
                    btn_no_data.setStyleSheet("background-color: white; color: black;")

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

    def get_training_dataset(self, selected_item):
        session = Session()
        X, y = [], []

        try:
            disk_type = session.query(DiskType).filter_by(name=selected_item).first()
            training_scans = session.query(DiskScan).filter(DiskScan.disk_type_id == disk_type.id, DiskScan.is_training==True).all()
            if training_scans:

                for scan in training_scans:
                    blades = session.query(Blade).filter_by(disk_scan_id=scan.id).all()
                for blade in blades:
                    if blade.prediction is None:
                        continue
                    wav_data = blade.scan
                    features = extract_features(wav_data)
                    X.append(features)
                    y.append(1 if blade.prediction is True else 0)
            else:
                logger.error("Ошибка: не выбраны данные")
                return False

        finally:
            session.close()

        return np.array(X, dtype=np.float32), np.array(y, dtype=np.float32)

    def train_model(self):
        selected_item = self.main_window.mt_disk_type.currentText()
        self.set_controls_enabled(False)
        QApplication.processEvents()
        data = self.get_training_dataset(selected_item)
        if not data:
            QMessageBox.warning(self, "Ошибка", "Обучение не совершено, нет данных")
            logger.error("Ошибка: Обучение отменено")
            self.set_controls_enabled(True)
            return
        else:
            X, y = data
        model = build_model(input_dim=5)
        history = model.fit(X,y, epochs=15, batch_size=8)
        self.save_model_to_db(model, selected_item)
        print(history.history)
        self.set_controls_enabled(True)
        self.show_info_message(f"Модель обучена: {history.history}")
        self.update_avaliable_models()

    def save_model_to_db(self, model, selected_item):
        session = Session()
        if selected_item:
            try:
                disk_type = session.query(DiskType).filter_by(name=selected_item).first()

                with tempfile.NamedTemporaryFile(suffix=".keras", delete=True) as tmp_file:
                    model.save(tmp_file.name)
                    tmp_file.seek(0)
                    model_bytes = tmp_file.read()

                encoded_model = base64.b64encode(model_bytes).decode('utf-8')
                new_model = DiskTypeModel(
                    disk_type_id=disk_type.id,
                    model=encoded_model,
                    is_current=False
                )
                session.add(new_model)
                session.commit()
                logger.info("Модель сохранена в базу данных")
            finally:
                session.close()

        else:
            logger.error("Ошибка, не найден disk_type")

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


