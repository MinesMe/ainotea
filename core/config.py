# file: core/config.py

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Класс для управления настройками приложения.
    """
    # --- Основные настройки ---
    DATABASE_URL: str

    # --- Настройки безопасности ---
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30

    # --- Настройки Google Cloud ---
    GOOGLE_APPLICATION_CREDENTIALS: str
    # GOOGLE_API_KEY: str  <-- ЗАКОММЕНТИРУЙТЕ ИЛИ УДАЛИТЕ ЭТУ СТРОКУ

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()