# file: core/config.py

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    """
    Класс для управления настройками приложения.
    Все поля сделаны необязательными для гарантированного запуска.
    """
    # --- СДЕЛАЕМ ВСЕ ПОЛЯ НЕОБЯЗАТЕЛЬНЫМИ ---
    DATABASE_URL: Optional[str] = None
    SECRET_KEY: Optional[str] = "default_secret_key_change_me" # Добавим значение по умолчанию
    OPENAI_API_KEY: Optional[str] = None
    # ------------------------------------

    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30

    model_config = SettingsConfigDict(env_file=".env", extra='ignore')

# Создаем один глобальный экземпляр настроек.
settings = Settings()

# --- ДИАГНОСТИЧЕСКИЙ ВЫВОД ---
# Этот код выполнится при старте и покажет, какие настройки были загружены.
print("--- Configuration Loaded ---")
print(f"DATABASE_URL is set: {settings.DATABASE_URL is not None}")
print(f"SECRET_KEY is set: {settings.SECRET_KEY is not None}")
print(f"OPENAI_API_KEY is set: {settings.OPENAI_API_KEY is not None}")
print("--------------------------")