# file: services/video_generator.py

import os
import subprocess
import math

# --- ЗАВИСИМОСТЬ ОТ GOOGLE CLOUD ПОЛНОСТЬЮ УДАЛЕНА ---
print("Video Generator: Google Cloud Text-to-Speech client is DISABLED.")


def create_video_from_summary(summary_text: str, background_video_path: str, voice_name: str) -> str:
    """
    Функция генерации видео временно отключена.

    Эта функция оставлена как "заглушка". При попытке ее вызова она
    немедленно вызовет ошибку, сообщая, что функционал не реализован.
    Это предотвращает попытки использовать нерабочий код и делает
    поведение API предсказуемым.
    """
    # Вызываем ошибку, чтобы явно показать, что функция не работает.
    raise NotImplementedError(
        "Video generation functionality is currently disabled because it depends on "
        "Google Cloud Text-to-Speech, which has been removed from the project."
    )

    # --- Весь код ниже оставлен как пример и никогда не будет выполнен ---

    # Функция для форматирования времени в формат SRT
    def format_time_srt(seconds: float) -> str:
        millisec = int((seconds - int(seconds)) * 1000)
        seconds = int(seconds)
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millisec:03d}"

    # 1. Генерация аудио (этот код больше не работает)
    # ...

    # 2. Создание файла субтитров
    # ...

    # 3. Сборка финального видео
    # ...

    # 4. Очистка
    # ...

    return ""