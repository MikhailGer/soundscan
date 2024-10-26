import os
import sys
import logging
from os import pread

# from PyQt5 import uic
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtCore import QEvent

from fixed_interface import Ui_SoundScan

from src.arduino.arduino_controller import ArduinoController
from src.windows.change_history import *
from src.windows.devise_config import *
from src.windows.disk_type import *
from src.windows.model_training import *
from src.windows.new_measurement import *

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

class MainWindow(QMainWindow, Ui_SoundScan):

    def __init__(self):
        super().__init__()
        self.on_tab_changed_lambda = None
        logger.info("Инициализация главного окна")  # Логирование инициализации главного окна
        try:
            # uic.loadUi('fixed_interface.ui', self)  # Загрузка интерфейса
            self.setupUi(self)
            logger.info("Интерфейс загружен успешно")
            # Инициализация контроллера Arduino
            # self.arduino = ArduinoController()
            # logger.info("Контроллер Arduino инициализирован")

            # Настройка различных вкладок
            # setup_new_measurement_tab(self, self.arduino)
            setup_new_measurement_tab(self)

            logger.info("Вкладка 'Новые измерения' настроена")

            setup_model_training_tab(self)
            logger.info("Вкладка 'Обучение ИИ' настроена")

            setup_change_history_tab(self)
            logger.info("Вкладка 'История измерений' настроена")

            setup_disk_type_tab(self)
            logger.info("Вкладка 'Типы дисков' настроена")

            setup_device_config_tab(self)
            logger.info("Вкладка 'Параметры устройства' настроена")

            self.setup_ui()

        except Exception as e:
            logger.error(f"Ошибка при инициализации главного окна: {e}", exc_info=True)

    def setup_ui(self):
        print('setup_ui')
        self.on_tab_changed_lambda = lambda index: self.on_tab_changed(index) #Сохраняем лямбду для того, чтобы можно было
        #отключить сигнал в new_measurmnet(чуток костыль)
        self.tabWidget.currentChanged.connect(self.on_tab_changed_lambda)

        #для блокировки интерфейса при сканировании (чуток костыль из за того что кнопка stop была засунута в tabwidget)
        self.tab_bar = self.tabWidget.tabBar()
        self.tab_bar.installEventFilter(self)

        self.tab_switching_enabled = True
        # self.nm_start.clicked.connect(self.start_scan)
        # self.nm_stop.clicked.connect(self.stop_scan)

    def eventFilter(self, source, event): #для блокировки возможности листать TabBar во время сканирования
        if source == self.tab_bar and not self.tab_switching_enabled:
            if event.type() in [QEvent.MouseButtonPress,
                                QEvent.MouseButtonRelease,
                                QEvent.MouseButtonDblClick,
                                QEvent.MouseMove,
                                QEvent.Wheel]:
                return True  # Блокируем событие
        return super(MainWindow, self).eventFilter(source, event)

    def on_tab_changed(self, index):
        print('on_tab_changed')

        if index == self.tabWidget.indexOf(self.change_history):
            logger.info("Вкладка 'История измерений' активна, обновляем список типов дисков")
            update_disk_type_combobox(self)
            
        elif index == self.tabWidget.indexOf(self.devise_config):
            logger.info("Вкладка 'Параметры установки' активна, загружаем конфигурацию устройства")
            load_device_config(self)
        
        elif index == self.tabWidget.indexOf(self.disk_type):
            logger.info("Переход на вкладку 'Типы дисков'. Обновление списка типов дисков.")
            load_disk_types(self)

        elif index == self.tabWidget.indexOf(self.model_training):
            logger.info("Переход на вкладку 'Обучение ИИ'. Обновление списка типов дисков.")
            update_disk_type_combobox(self)
        
        elif index == self.tabWidget.indexOf(self.new_measurement):
            logger.info("Переход на вкладку 'Новое измерение'. Обновление списка типов дисков.")
            load_disk_types_to_combobox(self)


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