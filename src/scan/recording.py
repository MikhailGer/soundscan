import io
import logging
import os
import shutil

import sounddevice as sd
import soundfile as sf
import numpy as np
import librosa
import librosa.display
import matplotlib.pyplot as plt
import scipy.signal as sg

logger = logging.getLogger(__name__)


class MicrophoneManagerSingleton:
    """
    Синглтон, который хранит настройки (частота дискретизации, кол-во каналов,
    имя аудиоинтерфейса) и при создании пытается установить нужное устройство.
    Обеспечивает методы record() и stripped_record() для получения WAV-байт.
    """

    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        """
        Если _instance ещё не создан, создаём, иначе возвращаем уже существующий.
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self,
                 device_name: str = "UMC204HD",
                 sample_rate: int = 192000,
                 channels: int = 1,
                 subtype: str = "PCM_24"):
        """
        Если объект ещё не инициализирован, сохраняем настройки и пытаемся
        найти устройство по имени. Если не находим, используем устройство
        по умолчанию (в системных настройках).
        """
        if not self._initialized:
            self.device_name = device_name
            self.sample_rate = sample_rate
            self.channels = channels
            self.subtype = subtype

            logger.info(f"Инициализация MicrophoneManagerSingleton "
                        f"(device='{device_name}', rate={sample_rate}, "
                        f"channels={channels}, subtype={subtype})")

            # Пытаемся найти устройство
            dev_idx = self._get_device_index(device_name, min_input_channels=channels)
            if dev_idx is not None:
                # Устанавливаем по умолчанию и для ввода, и для вывода
                sd.default.device = (dev_idx, dev_idx)
                selected_device = sd.query_devices(dev_idx)
                logger.info(f"Выбран аудиоинтерфейс: {selected_device['name']}")
            else:
                logger.warning(f"Устройство '{device_name}' не найдено. "
                               "Используется системное устройство по умолчанию.")

            self._initialized = True

    def record(self, duration: float) -> bytes:
        """
        Записывает аудио (float32), сохраняет в WAV (subtype) в оперативную память
        и возвращает байтовые данные.
        """
        logger.info(f"Начало записи: {duration} сек.")
        audio_data = sd.rec(
            frames=int(duration * self.sample_rate),
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype='float32'
        )
        sd.wait()
        logger.info("Запись завершена.")

        audio_buffer = io.BytesIO()
        sf.write(
            file=audio_buffer,
            data=audio_data,
            samplerate=self.sample_rate,
            format='WAV',
            subtype=self.subtype
        )
        wav_data = audio_buffer.getvalue()
        return wav_data

    def stripped_record(self, duration: float,
                        channel_idx: int = 0,
                        subtype: str = "PCM_24") -> bytes:
        """
        Записывает аудио или использует переданные WAV-байты, обрезает тишину
        (оставляя только область, где сигнал выше порога), добавляет 0.3 с «хвоста»
        и возвращает байты итогового WAV.
        """
        # 1. Записываем
        raw_data = self.record(duration)
        data, sr = sf.read(io.BytesIO(raw_data), dtype='float32')

        # 2. Выбираем нужный канал
        if data.ndim == 1:
            channel_data = data
        else:
            channel_data = data[:, channel_idx]

        # 3. Обрезаем тишину, оставляя только «громкий» участок + 0.3 с
        trimmed_audio = self._trim_keep_peaks(channel_data, sr, post_margin_s=0.3, threshold_ratio=0.1)

        # 4. Превращаем результат обратно в WAV-байты (моно)
        output_io = io.BytesIO()
        sf.write(output_io, trimmed_audio, sr, format='WAV', subtype=subtype)
        return output_io.getvalue()


    @staticmethod
    def _trim_keep_peaks(channel_data: np.ndarray,
                        samplerate: int,
                        post_margin_s: float = 0.3,
                        threshold_ratio: float = 0.1) -> np.ndarray:
        """
        Обрезает 'тихие' участки в начале и конце, оставляя только зону,
        где сигнал выше порога, плюс добавляет 0.3 с (по умолч.) после последнего пика.

        :param channel_data: Массив данных (1D, float32) для конкретного канала.
        :param samplerate: Частота дискретизации (Гц).
        :param post_margin_s: Сколько секунд сохранить после последнего «громкого» сэмпла.
        :param threshold_ratio: Порог определяется как max_amplitude * threshold_ratio.
        :return: Обрезанный массив (1D float32).
        """
        length = len(channel_data)
        if length == 0:
            return channel_data  # Пустой сигнал

        # 1. Вычисляем порог — возьмём долю от максимальной амплитуды сигнала
        max_amp = np.max(np.abs(channel_data))
        if max_amp == 0:
            # Сигнал нулевой — возвращаем «как есть»
            return channel_data

        threshold = max_amp * threshold_ratio

        # 2. Находим все сэмплы, где сигнал выше порога
        indices = np.where(np.abs(channel_data) > threshold)[0]
        if len(indices) == 0:
            # Нет ни одного сэмпла выше порога => возвращаем как есть или пустой
            return channel_data

        # 3. Определяем начало и конец «громкого» участка
        start_idx = indices[0]
        end_idx = indices[-1]

        # 4. Добавляем запас после последнего пика (0.3 с по умолчанию)
        end_idx += int(post_margin_s * samplerate)
        if end_idx >= length:
            end_idx = length - 1

        # 5. Вырезаем нужный фрагмент
        trimmed_audio = channel_data[start_idx:end_idx]
        return trimmed_audio

    @staticmethod
    def save_audio(audio_data: bytes,
                   filename: str = "record.wav",
                   sample_rate: int = 192000,
                   subtype='PCM_24'):
        """
        Сохраняет аудиосигнал (float32 или любой WAV-байт) в WAV-файл
        с помощью soundfile.
        """
        logger.info(f"Сохранение в файл: {filename} (subtype={subtype})")
        with open(filename, "wb") as f:
            f.write(audio_data)  # Пишем «как есть» (уже готовый WAV)
        logger.info("Сохранение завершено.")

    @staticmethod
    def _get_device_index(preferred_name: str, min_input_channels: int = 1) -> int | None:
        """
        Ищет в списке доступных устройств аудиоустройство, в названии
        которого содержится preferred_name. Возвращает индекс первого
        подходящего или None.
        """
        devices = sd.query_devices()
        for i, dev in enumerate(devices):
            if preferred_name in dev['name'] and dev['max_input_channels'] >= min_input_channels:
                return i
        return None
