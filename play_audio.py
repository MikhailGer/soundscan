93
import pyaudio
import wave
from src.db import Session
from src.models import Blade
import io

def play_audio_by_blade_id(blade_id):
    """
    Воспроизводит звук, сохраненный в записи Blade по указанному ID.
    :param blade_id: Идентификатор Blade в базе данных.
    """
    session = Session()
    try:
        # Получаем запись Blade по ID
        blade = session.query(Blade).get(blade_id)
        if blade is None:
            print(f"Blade с id {blade_id} не найден.")
            return
        
        # Проверяем наличие звуковых данных
        if not blade.scan:
            print(f"Blade с id {blade_id} не содержит данных звука.")
            return

        # Загружаем аудиоданные из базы
        audio_buffer = wave.open(io.BytesIO(blade.scan), 'rb')

        # Инициализируем PyAudio
        p = pyaudio.PyAudio()
        stream = p.open(
            format=p.get_format_from_width(audio_buffer.getsampwidth()),
            channels=audio_buffer.getnchannels(),
            rate=audio_buffer.getframerate(),
            output=True
        )

        print(f"Воспроизведение звука для Blade ID: {blade_id}")

        # Читаем и воспроизводим данные
        data = audio_buffer.readframes(1024)
        while data:
            stream.write(data)
            data = audio_buffer.readframes(1024)

        # Очищаем ресурсы
        stream.stop_stream()
        stream.close()
        p.terminate()

        print("Воспроизведение завершено.")
    except Exception as e:
        print(f"Ошибка при воспроизведении аудио: {e}")
    finally:
        session.close()

# Пример вызова функции
if __name__ == "__main__":
    blade_id = int(input("Введите ID Blade для воспроизведения звука: "))
    play_audio_by_blade_id(blade_id)
