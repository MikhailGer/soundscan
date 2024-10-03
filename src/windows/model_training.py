import logging
from functools import partial
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QListWidgetItem, QCheckBox, QWidget, QHBoxLayout, QTableWidgetItem, QHeaderView
from src.db import Session
from src.models import DiskType, DiskScan, Blade

# Настройка логирования
logger = logging.getLogger(__name__)



def setup_model_training_tab(main_window):
    """
    Настройка логики для вкладки "Обучение ИИ".
    """
    logger.info("Настройка вкладки 'Обучение ИИ'")
    # Привязываем события
    main_window.tabWidget.currentChanged.connect(lambda index: on_tab_changed(main_window, index))
    main_window.mt_disk_type.currentIndexChanged.connect(lambda: update_measurements(main_window))
    main_window.mt_measurements.itemSelectionChanged.connect(lambda: update_blade_results(main_window))


def on_tab_changed(main_window, index):
    """
    Событие при переключении вкладок. Обновляем ComboBox с типами дисков.
    """
    if index == main_window.tabWidget.indexOf(main_window.model_training):
        logger.info("Переход на вкладку 'Обучение ИИ'. Обновление списка типов дисков.")
        update_disk_type_combobox(main_window)


def update_disk_type_combobox(main_window):
    """
    Обновление ComboBox mt_disk_type из таблицы DiskType.
    """
    logger.info("Обновление ComboBox с типами дисков")
    session = Session()
    try:
        disk_types = session.query(DiskType).all()
        logger.info(f"Загружено {len(disk_types)} типов дисков")

        # Очищаем ComboBox и связанные элементы
        main_window.mt_disk_type.clear()
        main_window.mt_measurements.clear()
        main_window.mt_blade_results.clearContents()

        # Заполняем ComboBox типами дисков
        for disk_type in disk_types:
            main_window.mt_disk_type.addItem(disk_type.name, disk_type.id)
    except Exception as e:
        logger.error(f"Ошибка при загрузке типов дисков: {e}")
    finally:
        session.close()


def update_measurements(main_window):
    """
    Обновление ListWidget mt_measurements для выбранного типа диска.
    Добавление чекбоксов для изменения поля is_training.
    """
    selected_disk_type_id = main_window.mt_disk_type.currentData()  # Получаем ID выбранного типа диска
    logger.info(f"Обновление измерений для типа диска с ID {selected_disk_type_id}")

    if selected_disk_type_id:
        session = Session()
        try:
            disk_scans = session.query(DiskScan).filter_by(disk_type_id=selected_disk_type_id).all()
            logger.info(f"Загружено {len(disk_scans)} измерений для типа диска ID {selected_disk_type_id}")

            # Очищаем ListWidget
            main_window.mt_measurements.clear()

            # Заполняем ListWidget новыми измерениями и добавляем чекбоксы
            for scan in disk_scans:
                item = QListWidgetItem(main_window.mt_measurements)
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

                main_window.mt_measurements.setItemWidget(item, widget)
                checkbox.stateChanged.connect(partial(change_is_training_state, scan.id))
        except Exception as e:
            logger.error(f"Ошибка при обновлении измерений для типа диска ID {selected_disk_type_id}: {e}")
        finally:
            session.close()


def change_is_training_state(scan_id, state):
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


def update_blade_results(main_window):
    """
    Обновление QTableWidget mt_blade_results для выбранного измерения.
    """
    selected_measurement_item = main_window.mt_measurements.currentItem()
    if selected_measurement_item:
        selected_scan_id = selected_measurement_item.data(Qt.UserRole)  # Получаем ID измерения
        logger.info(f"Обновление результатов для измерения ID {selected_scan_id}")

        session = Session()
        try:
            blades = session.query(Blade).filter_by(disk_scan_id=selected_scan_id).all()
            logger.info(f"Загружено {len(blades)} лопаток для измерения ID {selected_scan_id}")

            main_window.mt_blade_results.clearContents()
            main_window.mt_blade_results.setRowCount(len(blades))  # Устанавливаем количество строк
            main_window.mt_blade_results.setColumnCount(3)
            main_window.mt_blade_results.setHorizontalHeaderLabels(["Номер лопатки", "Скан", "Дефект"])

            for row, blade in enumerate(blades):
                main_window.mt_blade_results.setItem(row, 0, QTableWidgetItem(str(blade.num)))
                main_window.mt_blade_results.setItem(row, 1, QTableWidgetItem(blade.scan))
                prediction = "Да" if blade.prediction else "Нет"
                main_window.mt_blade_results.setItem(row, 2, QTableWidgetItem(prediction))

            main_window.mt_blade_results.resizeColumnsToContents()
            main_window.mt_blade_results.resizeRowsToContents()

            header = main_window.mt_blade_results.horizontalHeader()
            header.setSectionResizeMode(QHeaderView.Stretch)
        except Exception as e:
            logger.error(f"Ошибка при обновлении результатов для измерения ID {selected_scan_id}: {e}")
        finally:
            session.close()
