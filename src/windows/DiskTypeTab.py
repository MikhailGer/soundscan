from datetime import datetime
import logging
from statistics import geometric_mean

from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtWidgets import QListWidget, QListWidgetItem, QMessageBox, QWidget
from sqlalchemy.orm import Session
from typing_extensions import reveal_type

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
        self.main_window.dt_blade_force.clear()
        self.main_window.dt_blade_distance.clear()
        self.main_window.dt_disk_types.setCurrentItem(None)
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
            dt_disk_diameter = int(self.main_window.dt_diameter.text()) if self.main_window.dt_diameter.text() else 0
            dt_disk_blade_distance = int(self.main_window.dt_blade_distance.text()) if self.main_window.dt_blade_distance.text() else 0
            dt_disk_blade_force = int(self.main_window.dt_blade_force.text()) if self.main_window.dt_blade_force.text() else 0

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
            new_disk_type.blade_force = dt_disk_blade_force
            session.add(new_disk_type)
            session.commit()
            logger.info(f"Новый тип диска добавлен: {new_disk_type.name}")

            # Добавляем новый элемент в список
            print(new_disk_type.name)
            item = QListWidgetItem(new_disk_type.name)
            item.setData(Qt.UserRole, new_disk_type.id)
            self.main_window.dt_disk_types.addItem(item)
            self.clear_disk_type_tab_fields()
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

        if not selected_item:
            logger.info("Не выбран диск для удаления")
            return

        disk_name = selected_item.text()
        if not self.removing_confirmation(disk_name):
            logger.info("Удаление отменено пользователем")
            return

        disk_type_id = selected_item.data(Qt.UserRole)
        logger.info(f"Удаление типа диска с ID {disk_type_id}")
        session = DatabaseSession()

        try:
            # Удаляем запись из базы данных
            disk_type = session.query(DiskType).get(disk_type_id)

            if not disk_type:
                logger.error(f"Тип диска с ID {disk_type_id} не найден")
                return


            session.delete(disk_type)
            session.commit()
            logger.info(f"Тип диска с ID {disk_type_id} удален")

            # Удаляем элемент из списка
            self.main_window.dt_disk_types.takeItem(self.main_window.dt_disk_types.row(selected_item))

            # чистим поля от старых данных
            self.clear_disk_type_tab_fields()

        except Exception as e:
            logger.error(f"Ошибка удаления типа диска с ID {disk_type_id}: {e}")
        finally:
            session.close()

    def removing_confirmation(self, disk_name):
        """
        Показывает диалоговое окно подтверждения удаления.
        :param disk_name: Имя диска, который собираемся удалить.
        :return: True, если пользователь подтвердил удаление; False в противном случае.
        """

        message = f"Вы действительно хотите удалить диск '{disk_name}' со всеми связанными сканированиями?"

        confirmation_box = QMessageBox()
        confirmation_box.setIcon(QMessageBox.Warning)
        confirmation_box.setWindowTitle("Подтверждение удаления")
        confirmation_box.setText(message)
        confirmation_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        confirmation_box.setDefaultButton(QMessageBox.No)

        # Показываем окно и получаем результат
        result = confirmation_box.exec_()
        return result == QMessageBox.Yes

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
                    self.main_window.dt_blade_force.setText(str(disk_type.blade_force))

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
        if not selected_item:
            logger.info("Не выбран диск для сохранения изменений")
            self.show_error_message("Выберите диск для сохранения изменений")
            return

        disk_type_id = selected_item.data(Qt.UserRole)
        logger.info(f"Сохранение изменений для типа диска с ID {disk_type_id}.")

        session = DatabaseSession()

        try:
            # Получаем тип диска
            disk_type = session.query(DiskType).get(disk_type_id)
            if not disk_type:
                logger.error(f"Тип диска с ID {disk_type_id} не найден в базе данных.")
                self.show_error_message("Выбранный диск не найден в базе данных.")
                return

            old_values = {
            "old_dt_name" : disk_type.name,
            "old_dt_diameter" : disk_type.diameter,
            "old_dt_blade_distance" : disk_type.blade_distance,
            "old_dt_blade_force" : disk_type.blade_force,

            }
            # Проверяем, что введены корректные числовые значения
            try:
                updated_values = {
                    "name" : self.main_window.dt_name.text() or old_values["old_dt_name"],
                    "diameter" : int(self.main_window.dt_diameter.text()) if self.main_window.dt_diameter.text() else old_values["old_dt_diameter"],
                    "blade_distance": int(self.main_window.dt_blade_distance.text()) if self.main_window.dt_blade_distance.text() else old_values["old_dt_blade_distance"],
                    "blade_force": int(self.main_window.dt_blade_force.text()) if self.main_window.dt_blade_force.text() else old_values["old_dt_blade_force"]
                }

            except ValueError:
                logger.warning("Некорректные числовые значения для диаметра или расстояния между лопатками")
                self.show_error_message("Введите корректные значения")
                show_error_message(
                    "Введите корректные числовые значения для диаметра и расстояния между лопатками.")
                return

            # Обновляем данные из полей
            if old_values != updated_values:
                disk_type.name = updated_values["name"]
                disk_type.diameter = updated_values["diameter"]
                disk_type.blade_distance = updated_values["blade_distance"]
                disk_type.blade_force = updated_values["blade_force"]

            # Сохраняем изменения в базе данных
            session.commit()
            logger.info(f"Изменения сохранены для типа диска с ID {disk_type_id}")

            # Обновляем текст выбранного элемента в QListWidget
            selected_item.setText(f"{disk_type.name} (ID:{disk_type.id})")

        except Exception as e:
            logger.error(f"Ошибка сохранения изменений для типа диска с ID {disk_type_id}: {e}")
        finally:
            session.close()
        self.main_window.dt_disk_types.setCurrentItem(None)



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
         
