import io
import logging
import math

import keras
import soundfile as sf
import scipy.signal as sg
import base64
import numpy as np
import tempfile

from keras.api.optimizers import SGD
from keras.src.metrics.accuracy_metrics import accuracy

from src.db import Session
from src.models import DiskTypeModel, DiskType, DiskScan, Blade

logger = logging.getLogger(__name__)


def load_model_from_db(disk_type_id):
    """
    Извлекает последнюю сохранённую модель для заданного типа диска из таблицы DiskTypeModel
    и возвращает десериализованный объект tf.keras.Model.
    """
    session = Session()
    try:
        #ищем установленную модель
        model_row = session.query(DiskTypeModel) \
            .filter(DiskTypeModel.disk_type_id == disk_type_id,DiskTypeModel.is_current == True) \
            .first()

        if not model_row:
            # Ищем последнюю модель (при желании можно искать по дате и т.д.)
            logger.warning(f"Нет установленной модели для disk_type_id={disk_type_id}")
            return None

            #ниже закоментирована возможность искать дополнительно просто последнюю модель

            # logger.warning(f"Попытка найти последнюю модель для disk_type_id={disk_type_id}")
            # model_row = session.query(DiskTypeModel) \
            #     .filter_by(disk_type_id=disk_type_id) \
            #     .order_by(DiskTypeModel.created_at.desc()) \
            #     .first()
            # if not model_row:
            #     logger.warning(f"Нет моделей для disk_type_id={disk_type_id}")
            #     return

        encoded_model = model_row.model
        model_bytes = base64.b64decode(encoded_model)
        with tempfile.NamedTemporaryFile(suffix=".keras", delete=True) as tmp_file:
            tmp_file.write(model_bytes)
            tmp_file.flush()
            loaded_model = keras.models.load_model(tmp_file.name)

        # model_buffer = io.BytesIO(model_bytes)
        # loaded_model = keras.models.load_model(model_buffer)

        return loaded_model

    except Exception as e:
        logger.error(f"Ошибка при загрузке модели из БД: {e}", exc_info=True)
        return None
    finally:
        session.close()


def extract_features(wav_data: bytes, nfft: int = 4096) -> list[float]:
    """
    Извлекает пять значений из суммарного спектра.
    wav_data — байты WAV-файла (моно или стерео).
    nfft — размер окна (NFFT) для sg.spectrogram.

    Возвращает список из пяти float-чисел.
    """
    # 1. Считываем WAV-байты как float32
    audio, sr = sf.read(io.BytesIO(wav_data), dtype='float32')
    # Если стерео — берём только левый канал
    if audio.ndim > 1:
        audio = audio[:, 0]

    # 2. Считаем спектр
    frequencies, times, spectrogram = sg.spectrogram(audio, sr, nfft=nfft)

    # 3. Превращаем спектр в "одномерный" путём суммирования по временной оси
    spectrogram_1d = np.sum(spectrogram, axis=1)  # shape: (num_freq_bins,)

    # 4. Подфункция для безопасного поиска argmax в заданном диапазоне
    def safe_argmax_in_range(arr: np.ndarray, start: int, end: int) -> float:
        """
        Возвращает argmax на подмассиве arr[start:end] как float,
        если этот подмассив не пустой; иначе 0.0
        """
        if start >= len(arr):  # выходим за границы
            return 0.0
        subarr = arr[start:end]
        if subarr.size == 0:
            return 0.0
        local_idx = np.argmax(subarr)
        return float(local_idx)

    # 5. Извлекаем пять значений
    #    (по сути индексы локального argmax в заданных диапазонах)
    value1 = safe_argmax_in_range(spectrogram_1d, 0, 200)
    value2 = safe_argmax_in_range(spectrogram_1d, 300, 500)
    value3 = safe_argmax_in_range(spectrogram_1d, 600, 1000)
    value4 = safe_argmax_in_range(spectrogram_1d, 1100, 1500)
    value5 = safe_argmax_in_range(spectrogram_1d, 1600, 2000)

    return [value1, value2, value3, value4, value5]


def build_model(input_dim, output_dim=1):
    """
    Создаёт и компилирует Keras-модель для регрессии (активация 'tanh' в выходном слое).

    :param input_dim: размерность входных данных (количество признаков)
    :param output_dim: размерность выхода (в данном примере = 1)
    :return: скомпилированная модель
    """
    model = keras.Sequential()
    model.add(keras.layers.Dense(16, input_dim=input_dim, activation='relu'))
    model.add(keras.layers.Dense(32, activation='tanh'))
    # model.add(keras.layers.Dense(output_dim, activation='tanh'))
    #Пробую изменить выходной слой чтобы на выходе получать бинарную классификацию для однозначной оценки True или False
    model.add(keras.layers.Dense(1, activation='sigmoid'))


    optimizer = SGD(learning_rate=0.001, momentum=0.5, nesterov=True)
    # model.compile(loss='mean_squared_error', optimizer=optimizer, metrics=['accuracy'])
    model.compile(loss='binary_crossentropy', optimizer=optimizer, metrics=['accuracy'])

    return model

def calc_correlation(y_true, y_pred):
    """
    Считает коэффициент корреляции Пирсона между векторами y_true и y_pred.

    :param y_true: истинные значения
    :param y_pred: предсказанные значения
    :return: коэффициент корреляции (float)
    """
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)

    mean_true = np.mean(y_true)
    mean_pred = np.mean(y_pred)

    sum1 = np.sum((y_true - mean_true) * (y_pred - mean_pred))
    sum2 = np.sum((y_pred - mean_pred) ** 2)
    sum3 = np.sum((y_true - mean_true) ** 2)

    # Защита от деления на ноль
    denominator = math.sqrt(sum2 * sum3)
    if denominator == 0:
        return 0
    return sum1 / denominator

def get_training_dataset(selected_item):
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


def save_model_to_db(model, selected_item):
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
        return False

    return True

