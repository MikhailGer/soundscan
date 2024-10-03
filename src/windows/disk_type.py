from datetime import datetime
import logging
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QListWidgetItem, QMessageBox
from sqlalchemy.orm import Session
from src.db import Session as DatabaseSession
from src.models import DiskType
from PyQt5.QtGui import QStandardItemModel, QStandardItem

# Настройка логирования
logger = logging.getLogger(__name__)


def setup_disk_type_tab(main_window):
    """
    Настройка логики для вкладки "Типы дисков".
    """
    logger.info("Настройка вкладки 'Типы дисков'")
    # Подгружаем данные при переходе на вкладку
    main_window.tabWidget.currentChanged.connect(lambda index: on_tab_changed(main_window, index))

    # Привязываем события к кнопкам
    main_window.dt_add.clicked.connect(lambda: add_disk_type(main_window))
    main_window.dt_drop.clicked.connect(lambda: remove_disk_type(main_window))
    main_window.dt_save.clicked.connect(lambda: save_disk_type_changes(main_window))

    # Подключение события выбора для QListWidget
    main_window.dt_disk_types.itemSelectionChanged.connect(lambda: update_disk_type_details(main_window))


def on_tab_changed(main_window, index):
    """
    Событие при переключении вкладок. Обновляем список типов дисков.
    """
    if index == main_window.tabWidget.indexOf(main_window.disk_type):
        logger.info("Переход на вкладку 'Типы дисков'. Обновление списка типов дисков.")
        load_disk_types(main_window)


def load_disk_types(main_window):
    """
    Загрузка всех типов дисков из базы данных в dt_disk_types.
    """
    logger.info("Загрузка типов дисков из базы данных")
    session = DatabaseSession()
    try:
        disk_types = session.query(DiskType).all()
        logger.info(f"Загружено {len(disk_types)} типов дисков")

        # Очищаем список перед добавлением новых элементов
        main_window.dt_disk_types.clear()

        # Заполняем список элементами
        for disk_type in disk_types:
            item = QListWidgetItem(disk_type.name)
            item.setData(Qt.UserRole, disk_type.id)  # Сохраняем ID диска
            main_window.dt_disk_types.addItem(item)
    except Exception as e:
        logger.error(f"Ошибка загрузки типов дисков: {e}")
    finally:
        session.close()


def add_disk_type(main_window):
    """
    Добавление нового типа диска в базу данных и отображение в списке.
    """
    logger.info("Добавление нового типа диска")
    session = DatabaseSession()
    try:
        # Создаем новый тип диска
        new_disk_type = DiskType(
            name=f"{datetime.now()} New disk type",
        )
        session.add(new_disk_type)
        session.commit()
        logger.info(f"Новый тип диска добавлен: {new_disk_type.name}")

        # Добавляем новый элемент в список
        item = QListWidgetItem(new_disk_type.name)
        item.setData(Qt.UserRole, new_disk_type.id)
        main_window.dt_disk_types.addItem(item)
    except Exception as e:
        logger.error(f"Ошибка добавления нового типа диска: {e}")
    finally:
        session.close()


def remove_disk_type(main_window):
    """
    Удаление выбранного типа диска из базы данных и списка.
    """
    selected_item = main_window.dt_disk_types.currentItem()

    if selected_item:
        disk_type_id = selected_item.data(Qt.UserRole)
        logger.info(f"Удаление типа диска с ID {disk_type_id}")
        session = DatabaseSession()
        try:
            # Удаляем запись из базы данных
            disk_type = session.query(DiskType).get(disk_type_id)
            session.delete(disk_type)
            session.commit()
            logger.info(f"Тип диска с ID {disk_type_id} удален")

            # Удаляем элемент из списка
            main_window.dt_disk_types.takeItem(main_window.dt_disk_types.row(selected_item))
        except Exception as e:
            logger.error(f"Ошибка удаления типа диска с ID {disk_type_id}: {e}")
        finally:
            session.close()


def update_disk_type_details(main_window):
    """
    Обновление полей dt_name, dt_diameter, dt_blade_distance при выборе элемента в dt_disk_types.
    """
    selected_item = main_window.dt_disk_types.currentItem()

    if selected_item:
        disk_type_id = selected_item.data(Qt.UserRole)  # Получаем ID типа диска
        logger.info(f"Выбран тип диска с ID {disk_type_id}")

        session = DatabaseSession()
        try:
            # Находим запись в базе данных по ID
            disk_type = session.query(DiskType).get(disk_type_id)

            if disk_type:
                # Обновляем поля значениями из выбранной записи
                main_window.dt_name.setText(disk_type.name)
                main_window.dt_diameter.setText(str(disk_type.diameter))
                main_window.dt_blade_distance.setText(str(disk_type.blade_distance))
                logger.info(f"Поля обновлены для типа диска: {disk_type.name}")
            else:
                logger.warning(f"Тип диска с ID {disk_type_id} не найден в базе данных.")
        except Exception as e:
            logger.error(f"Ошибка обновления данных типа диска с ID {disk_type_id}: {e}")
        finally:
            session.close()


def save_disk_type_changes(main_window):
    """
    Сохранение изменений в базе данных для выбранного типа диска с проверкой числовых значений.
    """
    selected_item = main_window.dt_disk_types.currentItem()

    if selected_item:
        disk_type_id = selected_item.data(Qt.UserRole)
        logger.info(f"Сохранение изменений для типа диска с ID {disk_type_id}")
        session = DatabaseSession()
        try:
            # Получаем тип диска
            disk_type = session.query(DiskType).get(disk_type_id)

            # Проверяем, что введены корректные числовые значения
            try:
                diameter = int(main_window.dt_diameter.text())
                blade_distance = int(main_window.dt_blade_distance.text())
            except ValueError:
                logger.warning("Некорректные числовые значения для диаметра или расстояния между лопатками")
                show_error_message("Введите корректные числовые значения для диаметра и расстояния между лопатками.")
                return

            # Обновляем данные из полей
            disk_type.name = main_window.dt_name.text()
            disk_type.diameter = diameter
            disk_type.blade_distance = blade_distance

            # Сохраняем изменения в базе данных
            session.commit()
            logger.info(f"Изменения сохранены для типа диска с ID {disk_type_id}")

            # Обновляем текст выбранного элемента в QListWidget
            selected_item.setText(disk_type.name)

        except Exception as e:
            logger.error(f"Ошибка сохранения изменений для типа диска с ID {disk_type_id}: {e}")
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
