# from PyQt5 import uic
from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtCore import QEvent, pyqtSlot

#стабильная но устаревшая версия интерфейса
# from src.interfaces.fixed_interface_2 import Ui_SoundScan

from src.interfaces.fixed_interface_2_2 import Ui_SoundScan

from src.arduino.arduino_controller import ArduinoController

from src.windows.change_history import *
from src.windows.model_training import *
from src.windows.new_measurement import *

from src.windows.DiskTypeTab import DiskTypeTab
from src.windows.DeviceConfigTab import DeviceConfigTab

logger = logging.getLogger(__name__)

class MainWindow(QMainWindow, Ui_SoundScan):

    def __init__(self):
        super().__init__()
        self.tabs = {} #словарь для управления вкладками

        self.tabs['disk_type'] = DiskTypeTab(self)
        self.tabs['device_config'] = DeviceConfigTab(self)

        self.current_tab = None

        self.on_tab_changed_lambda = None
        logger.info("Инициализация главного окна")  # Логирование инициализации главного окна
        try:
            self.setupUi(self)
            logger.info("Интерфейс загружен успешно")
            # Инициализация контроллера Arduino
            # self.arduino = ArduinoController()
            # logger.info("Контроллер Arduino инициализирован")

            # Настройка различных вкладок
            setup_new_measurement_tab(self)

            logger.info("Вкладка 'Новые измерения' настроена")

            setup_model_training_tab(self)
            logger.info("Вкладка 'Обучение ИИ' настроена")

            setup_change_history_tab(self)
            logger.info("Вкладка 'История измерений' настроена")

            # self.disk_type_tab = DiskTypeTab(self)
            # logger.info("Вкладка 'Типы дисков' настроена")
            #
            # self.devise_config_tab = DeviceConfigTab(self)
            # logger.info("Вкладка 'Параметры устройства' настроена")

            self.connection_established = False
            self.arduino_worker = ArduinoController().create_worker()
            self.arduino_worker.connection_established.connect(self.on_connection_established)  # Подключаем обработчик состояния подключения
            self.arduino_worker.start()  # Запуск потока
            self.setup_ui()

        except Exception as e:
            logger.error(f"Ошибка при инициализации главного окна: {e}", exc_info=True)

    # Обработка статуса подключения
    @pyqtSlot(bool)
    def on_connection_established(self, connected):
        if connected:
            self.connection_established = True
            logger.info("Подключено к Ардуино!.")
            set_controls_enabled(self, True)
        else:
            logger.info("Ошибка подключения к Arduino.")

    def setup_ui(self):
        print('setup_ui')

        self.on_tab_changed_lambda = lambda index: self.on_tab_changed(
            index)  # Сохраняем лямбду для того, чтобы можно было
        # отключить сигнал в new_measurmnet(чуток костыль)
        self.tabWidget.currentChanged.connect(self.on_tab_changed_lambda)
        self.nm_disk_type.currentIndexChanged.connect(lambda: update_blade_fields(self))
        # для блокировки интерфейса при сканировании (чуток костыль из-за того что кнопка stop была засунута в tabwidget)
        self.tab_bar = self.tabWidget.tabBar()
        self.tab_bar.installEventFilter(self)

        self.tab_switching_enabled = True

        self.on_tab_changed(self.tabWidget.currentIndex()) #прогрузить первую страницу, которая выставлена по умолчанию

    def eventFilter(self, source, event):  # для блокировки возможности листать TabBar во время сканирования
        if source == self.tab_bar and not self.tab_switching_enabled:
            if event.type() in [QEvent.MouseButtonPress,
                                QEvent.MouseButtonRelease,
                                QEvent.MouseButtonDblClick,
                                QEvent.MouseMove,
                                QEvent.Wheel]:
                return True  # Блокируем событие
        return super(MainWindow, self).eventFilter(source, event)

    def on_tab_changed(self, index):
        logger.info("Вкладка изменена")
        tab_name = None

        if index == self.tabWidget.indexOf(self.change_history):
            logger.info("Вкладка 'История измерений' активна, обновляем список типов дисков")
            update_disk_type_combobox(self)

        elif index == self.tabWidget.indexOf(self.devise_config):
            logger.info("Вкладка 'Параметры установки' активна, загружаем конфигурацию устройства")
            # self.devise_config_tab.load_device_config()
            tab_name = 'device_config'

        elif index == self.tabWidget.indexOf(self.disk_type):
            # self.disk_type_tab.clear_disk_type_tab_fields()
            # self.disk_type_tab.load_disk_types()
            tab_name = 'disk_type'
            logger.info("Переход на вкладку 'Типы дисков'. Обновление списка типов дисков.")

        elif index == self.tabWidget.indexOf(self.model_training):
            logger.info("Переход на вкладку 'Обучение ИИ'. Обновление списка типов дисков.")
            update_disk_type_combobox(self)

        elif index == self.tabWidget.indexOf(self.new_measurement):
            logger.info("Переход на вкладку 'Новое измерение'. Обновление списка типов дисков.")
            load_disk_types_to_combobox(self)

        if tab_name:
            self.activate_tab(tab_name)


    def activate_tab(self, tab_name):
        for name, tab in self.tabs.items(): #отключаем сигналы для всех вкладок, чтобы не оставалось "хвостов"
            if name != tab_name:
                tab.disconnect_signals()

        if tab_name in self.tabs:
            self.tabs[tab_name].connect_signals()
            self.tabs[tab_name].start_tab()
            self.current_tab = tab_name
            logger.info(f"Активирована вкладка {self.current_tab}")


