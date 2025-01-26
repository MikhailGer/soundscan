# from PyQt5 import uic
from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtCore import QEvent, pyqtSlot

#стабильная но устаревшая версия интерфейса
# from src.interfaces.fixed_interface_2 import Ui_SoundScan

from src.interfaces.fixed_interface_2_2 import Ui_SoundScan

from src.arduino.arduino_controller import ArduinoController

from src.windows.model_training import *

from src.windows.ChangeHistoryTab import ChangeHistoryTab
from src.windows.NewMeasurementTab import NewMeasurementTab
from src.windows.DiskTypeTab import DiskTypeTab
from src.windows.DeviceConfigTab import DeviceConfigTab

logger = logging.getLogger(__name__)

class MainWindow(QMainWindow, Ui_SoundScan):

    def __init__(self):
        super().__init__()
        self.tabs = {} #словарь для управления вкладками

        self.current_tab = None
        self.on_tab_changed_lambda = None
        logger.info("Инициализация главного окна")  # Логирование инициализации главного окна
        try:
            self.setupUi(self)
            # инициализируем вкладки после SetupUI
            self.tabs['disk_type'] = DiskTypeTab(self)
            self.tabs['device_config'] = DeviceConfigTab(self)
            self.tabs['new_measurement'] = NewMeasurementTab(self)
            self.tabs['change_history'] = ChangeHistoryTab(self)
            logger.info("Интерфейс загружен успешно")

            #Вкладки ниже еще не реализованы в виде классов(пока особо не нужны)
            setup_model_training_tab(self)
            logger.info("Вкладка 'Обучение ИИ' настроена")



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

        self.tabWidget.currentChanged.connect(self.on_tab_changed)
        self.nm_disk_type.currentIndexChanged.connect(self.tabs["new_measurement"].update_blade_fields) #привязываем сигнал
        # появления новых лопаток к имеющейся вкладке new measurement

        # для блокировки интерфейса при сканировании (чуток костыль из-за того что кнопка styyop была засунута в tabwidget)
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
        for name, tab in self.tabs.items(): #отключаем сигналы для всех вкладок, чтобы не оставалось "хвостов(не срабатывали действия для старых вкладок)"
            if name != tab_name:
                tab.disconnect_signals() #В каждом классе должны быть прописаны методы connect_signals и disconnect_signals

        if index == self.tabWidget.indexOf(self.change_history):
            logger.info("Вкладка 'История измерений' активна, обновляем список типов дисков")
            tab_name = 'change_history'

        elif index == self.tabWidget.indexOf(self.devise_config):
            logger.info("Вкладка 'Параметры установки' активна, загружаем конфигурацию устройства")
            tab_name = 'device_config'

        elif index == self.tabWidget.indexOf(self.disk_type):
            logger.info("Переход на вкладку 'Типы дисков'. Обновление списка типов дисков.")
            tab_name = 'disk_type'

        elif index == self.tabWidget.indexOf(self.model_training):
            logger.info("Переход на вкладку 'Обучение ИИ'. Обновление списка типов дисков.")
            update_disk_type_combobox(self)

        elif index == self.tabWidget.indexOf(self.new_measurement):
            logger.info("Переход на вкладку 'Новое измерение'. Обновление списка типов дисков.")
            tab_name = 'new_measurement'

        if tab_name:
            self.activate_tab(tab_name)


    def activate_tab(self, tab_name):
        # for name, tab in self.tabs.items(): #отключаем сигналы для всех вкладок, чтобы не оставалось "хвостов(не срабатывали действия для старых вкладок)"
        #     if name != tab_name:
        #         tab.disconnect_signals() #В каждом классе должны быть прописаны методы connect_signals и disconnect_signals

        if tab_name in self.tabs:
            self.tabs[tab_name].connect_signals()
            self.tabs[tab_name].start_tab()
            self.current_tab = tab_name
            logger.info(f"Активирована вкладка {self.current_tab}")
        else:
            logger.info(f"Такой вкладки не существует")
