# file: core/config.py

from typing import Optional # <-- ДОБАВЛЕН ЭТОТ ИМПОРТ
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Класс для управления настройками приложения.
    Он автоматически читает переменные из файла .env и системных переменных окружения.
    """
    # --- Основные настройки ---
    DATABASE_URL: str

    # --- Настройки безопасности ---
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30

    # --- Настройки Google Cloud ---
    # Сделаем эту переменную НЕОБЯЗАТЕЛЬНОЙ, задав значение по умолчанию None
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = None

    # Конфигурация Pydantic для чтения из файла .env
    model_config = SettingsConfigDict(env_file=".env")


# Создаем один глобальный экземпляр настроек,
# который будет использоваться во всем приложении.
settings = Settings()