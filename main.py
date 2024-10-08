import os
import sys
import logging
from PyQt5 import uic
from PyQt5.QtWidgets import QApplication, QMainWindow

from src.arduino.arduino_controller import ArduinoController
from src.windows.change_history import setup_change_history_tab
from src.windows.devise_config import setup_device_config_tab
from src.windows.disk_type import setup_disk_type_tab
from src.windows.model_training import setup_model_training_tab
from src.windows.new_measurement import setup_new_measurement_tab

# Конфигурация логирования
logging.basicConfig(
    level=logging.DEBUG,  # Установить уровень логирования
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Формат сообщений
    handlers=[
        logging.FileHandler("application.log"),  # Запись логов в файл
        logging.StreamHandler(sys.stdout)  # Вывод логов в консоль
    ]
)

# Создаем отдельный логгер для текущего модуля
logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        logger.info("Инициализация главного окна")  # Логирование инициализации главного окна
        try:
            uic.loadUi('interface.ui', self)  # Загрузка интерфейса
            logger.info("Интерфейс загружен успешно")

            # Инициализация контроллера Arduino
            self.arduino = ArduinoController(self)
            logger.info("Контроллер Arduino инициализирован")

            # Настройка различных вкладок
            setup_new_measurement_tab(self, self.arduino)
            logger.info("Вкладка 'Новые измерения' настроена")

            setup_model_training_tab(self)
            logger.info("Вкладка 'Обучение ИИ' настроена")

            setup_change_history_tab(self)
            logger.info("Вкладка 'История измерений' настроена")

            setup_disk_type_tab(self)
            logger.info("Вкладка 'Типы дисков' настроена")

            setup_device_config_tab(self)
            logger.info("Вкладка 'Параметры устройства' настроена")

        except Exception as e:
            logger.error(f"Ошибка при инициализации главного окна: {e}", exc_info=True)

if __name__ == "__main__":
    logger.info("Запуск приложения")  # Логирование начала выполнения программы
    os.remove("application.log")
    app = QApplication(sys.argv)

    try:
        # Создаем главное окно
        window = MainWindow()
        window.show()
        logger.info("Главное окно успешно создано и отображено")
    except Exception as e:
        logger.critical(f"Критическая ошибка при запуске приложения: {e}", exc_info=True)
        sys.exit(1)

    sys.exit(app.exec_())