# file: services/storage.py

import os
import shutil
import uuid
from fastapi import UploadFile

class FileStorage:
    """
    Сервис для сохранения и получения URL загруженных файлов.

    ВНИМАНИЕ: Эта реализация сохраняет файлы на локальный диск.
    Она подходит для локальной разработки, но не для production на платформах
    с эфемерной файловой системой, таких как Railway.
    Для production этот класс следует заменить на клиент для облачного хранилища.
    """
    def __init__(self, base_path: str = "uploads"):
        self.base_path = base_path
        # Убедимся, что директория для загрузок существует
        if not os.path.exists(self.base_path):
            os.makedirs(self.base_path)

    def save_file(self, file: UploadFile) -> str:
        """
        Сохраняет загруженный файл на диск.

        :param file: Объект UploadFile от FastAPI.
        :return: Относительный путь к сохраненному файлу.
        """
        try:
            # Генерируем уникальное имя файла, чтобы избежать перезаписи
            # и проблем с одинаковыми именами. Сохраняем исходное расширение.
            file_extension = os.path.splitext(file.filename)[1]
            unique_filename = f"{uuid.uuid4().hex}{file_extension}"
            file_path = os.path.join(self.base_path, unique_filename)

            # Копируем содержимое загруженного файла в новый файл на диске
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            # Возвращаем путь, который мы сохраним в базу данных
            return file_path
        finally:
            # Закрываем файл, чтобы освободить ресурсы
            file.file.close()

    def get_file_url(self, file_path: str) -> str:
        """
        Преобразует локальный путь к файлу в URL, доступный через API.

        :param file_path: Локальный путь к файлу (например, 'uploads/xyz.jpg').
        :return: URL, по которому можно будет получить доступ к файлу.
        """
        # Мы настроим в main.py статическую директорию,
        # чтобы файлы из папки 'uploads' были доступны по URL '/uploads/...'
        return f"/{file_path}"

# Создаем один экземпляр сервиса, который будем использовать во всем приложении.
# Это называется Singleton pattern.
file_storage = FileStorage()