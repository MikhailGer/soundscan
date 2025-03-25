import os
import sys

# from PyQt5 import uic
from PyQt5.QtWidgets import QApplication

from src.windows.NewMeasurementTab import *
from src.windows.main_window import MainWindow
from src.scan.recording import MicrophoneManagerSingleton


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


if __name__ == "__main__":
    logger.info("Запуск приложения")  # Логирование начала выполнения программы
    mic = MicrophoneManagerSingleton()
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