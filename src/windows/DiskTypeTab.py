from datetime import datetime
import logging
from statistics import geometric_mean

from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtWidgets import QListWidget, QListWidgetItem, QMessageBox, QWidget
from sqlalchemy.orm import Session
from src.db import Session as DatabaseSession
from src.models import DiskType

logger = logging.getLogger(__name__)


class DiskTypeTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.main_window.installEventFilter(self)
        self.setup_disk_type_tab()


    def setup_disk_type_tab(self):
        """
           Настройка логики для вкладки "Типы дисков".
           """
        logger.info("Настройка вкладки 'Типы дисков'")

        # Привязываем события
        self.main_window.dt_add.clicked.connect(self.add_disk_type)
        self.main_window.dt_drop.clicked.connect(self.remove_disk_type)
        self.main_window.dt_save.clicked.connect(self.save_disk_type_changes)
        self.main_window.dt_disk_types.itemClicked.connect(self.on_item_clicked)
        # Подключение события выбора для QListWidget
        # self.main_window.dt_disk_types.itemSelectionChanged.connect(self.update_disk_type_details)

    def eventFilter(self, source, event):
        """
        Обработка кликов по окну.
        Если клик вне области dt_disk_types, сбрасываем выделение.
        """
        if event.type() == QEvent.MouseButtonPress:
            if source != self.main_window.dt_disk_types.viewport():
                logger.info("Клик за пределами списка, сброс выделения")
                self.clear_disk_type_tab_fields()
                return True
        return super().eventFilter(source, event)


    def clear_disk_type_tab_fields(self):
        self.main_window.dt_disk_types.clearSelection()
        self.main_window.dt_name.clear()
        self.main_window.dt_diameter.clear()
        self.main_window.dt_blade_distance.clear()
        logger.info("Поля очищены")
    
    def on_item_clicked(self, item):
        logger.info(f"Выбран элемент {item.text()}")
        self.update_disk_type_details()
    
    def load_disk_types(self):
        """
        Загрузка всех типов дисков из базы данных в dt_disk_types.
        """
        logger.info("Загрузка типов дисков из базы данных")

        session = DatabaseSession()
        try:
            disk_types = session.query(DiskType).all()
            logger.info(f"Загружено {len(disk_types)} типов дисков")

            # Очищаем список перед добавлением новых элементов
            self.main_window.dt_disk_types.clear()

            # Заполняем список элементами
            for disk_type in disk_types:
                item = QListWidgetItem(f"{disk_type.name} (ID:{disk_type.id})")
                item.setData(Qt.UserRole, disk_type.id)  # Сохраняем ID диска
                self.main_window.dt_disk_types.addItem(item)
        except Exception as e:
            logger.error(f"Ошибка загрузки типов дисков: {e}")
        finally:
            session.close()

    def add_disk_type(self):
        """
        Добавление нового типа диска в базу данных и отображение в списке.
        """
        logger.info("Добавление нового типа диска")
        session = DatabaseSession()
        try:
            dt_disk_type_name = self.main_window.dt_name.text() if self.main_window.dt_name.text() else "New disk type"
            dt_disk_diameter = float(self.main_window.dt_diameter.text()) if self.main_window.dt_diameter.text() else 0
            dt_disk_blade_distance = float(
                self.main_window.dt_blade_distance.text()) if self.main_window.dt_blade_distance.text() else 0

        except ValueError as e:
            logger.warning(f"Некорректное значение: {e}")
            show_error_message("Пожалуйста, введите корректные числовые значения.")
            return

        try:
            # Создаем новый тип диска
            new_disk_type = DiskType(
                name=f"{datetime.now()} {dt_disk_type_name}",
            )
            new_disk_type.diameter = dt_disk_diameter
            new_disk_type.blade_distance = dt_disk_blade_distance
            session.add(new_disk_type)
            session.commit()
            logger.info(f"Новый тип диска добавлен: {new_disk_type.name}")

            # Добавляем новый элемент в список
            print(new_disk_type.name)
            item = QListWidgetItem(new_disk_type.name)
            item.setData(Qt.UserRole, new_disk_type.id)
            self.main_window.dt_disk_types.addItem(item)
            self.load_disk_types()
        except Exception as e:
            logger.error(f"Ошибка добавления нового типа диска: {e}")
        finally:
            session.close()

    def remove_disk_type(self):
        """
        Удаление выбранного типа диска из базы данных и списка.
        """
        selected_item = self.main_window.dt_disk_types.currentItem()

        if selected_item:
            disk_type_id = selected_item.data(Qt.UserRole)
            logger.info(f"Удаление типа диска с ID {disk_type_id}")
            session = DatabaseSession()
            try:
                # Удаляем запись из базы данных
                disk_type = session.query(DiskType).get(disk_type_id)
                if disk_type:
                    session.delete(disk_type)
                    session.commit()
                    # ...
                    self.main_window.dt_name.clear()
                    self.main_window.dt_diameter.clear()
                    self.main_window.dt_blade_distance.clear()

                else:
                    logger.error(f"Тип диска с ID {disk_type_id} не найден")

                logger.info(f"Тип диска с ID {disk_type_id} удален")

                # Удаляем элемент из списка
                self.main_window.dt_disk_types.takeItem(self.main_window.dt_disk_types.row(selected_item))
                # чистим поля от старых данных


            except Exception as e:
                logger.error(f"Ошибка удаления типа диска с ID {disk_type_id}: {e}")
            finally:
                session.close()

    def update_disk_type_details(self):
        """
        Обновление полей dt_name, dt_diameter, dt_blade_distance при выборе элемента в dt_disk_types.
        """
        print("here")
        selected_item = self.main_window.dt_disk_types.currentItem()
        if selected_item:
            disk_type_id = selected_item.data(Qt.UserRole)  # Получаем ID типа диска
            logger.info(f"Выбран тип диска с ID {disk_type_id}")

            session = DatabaseSession()
            try:
                # Находим запись в базе данных по ID
                disk_type = session.query(DiskType).get(disk_type_id)

                if disk_type:
                    # Обновляем поля значениями из выбранной записи
                    self.main_window.dt_name.setText(f"{disk_type.name}")
                    self.main_window.dt_diameter.setText(str(disk_type.diameter))
                    self.main_window.dt_blade_distance.setText(str(disk_type.blade_distance))
                    logger.info(f"Поля обновлены для типа диска: {disk_type.name}")
                else:
                    logger.warning(f"Тип диска с ID {disk_type_id} не найден в базе данных.")

            except ValueError as e:
                logger.warning(f"Некорректное значение: {e}")
            except Exception as e:
                logger.error(f"Ошибка обновления данных типа диска с ID {disk_type_id}: {e}")
            finally:
                session.close()

    def save_disk_type_changes(self):
        """
        Сохранение изменений в базе данных для выбранного типа диска с проверкой числовых значений.
        """
        selected_item = self.main_window.dt_disk_types.currentItem()

        if selected_item:
            disk_type_id = selected_item.data(Qt.UserRole)
            logger.info(f"Сохранение изменений для типа диска с ID {disk_type_id}")
            session = DatabaseSession()
            try:
                # Получаем тип диска
                disk_type = session.query(DiskType).get(disk_type_id)

                # Проверяем, что введены корректные числовые значения
                try:
                    dt_disk_type_name = self.main_window.dt_name.text() if self.main_window.dt_name.text() else "New disk type"
                    diameter = int(self.main_window.dt_diameter.text())
                    blade_distance = int(self.main_window.dt_blade_distance.text())
                except ValueError:
                    logger.warning("Некорректные числовые значения для диаметра или расстояния между лопатками")
                    self.show_error_message("Введите корректные значения")
                    show_error_message(
                        "Введите корректные числовые значения для диаметра и расстояния между лопатками.")
                    return

                # Обновляем данные из полей
                disk_type.name = dt_disk_type_name
                disk_type.diameter = diameter
                disk_type.blade_distance = blade_distance

                # Сохраняем изменения в базе данных
                session.commit()
                logger.info(f"Изменения сохранены для типа диска с ID {disk_type_id}")

                # Обновляем текст выбранного элемента в QListWidget
                selected_item.setText(f"{disk_type.name} (ID:{disk_type.id})")

            except Exception as e:
                logger.error(f"Ошибка сохранения изменений для типа диска с ID {disk_type_id}: {e}")
            finally:
                session.close()


    def show_error_message(self, message):
        """
        Показать сообщение об ошибке.
        """
        logger.error(f"Показ сообщения об ошибке: {message}")
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setText(message)
        msg.setWindowTitle("Ошибка")
        msg.exec_()
         
