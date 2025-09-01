# file: core/config.py

from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from typing import Optional

# Этот блок кода вычисляет, где должен находиться .env файл,
# но не требует его обязательного наличия.
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE_PATH = BASE_DIR / ".env"

class Settings(BaseSettings):
    """
    Класс для управления настройками приложения.
    """
    
    # Переменные сделаны необязательными (Optional).
    # Это позволяет приложению успешно собраться (build) на Railway,
    # даже если переменные окружения еще не установлены.
    OPENAI_API_KEY: Optional[str] = None
    DATABASE_URL: Optional[str] = None
    SECRET_KEY: Optional[str] = None

    # Эти переменные можно оставить обязательными, так как у них есть значения по умолчанию
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30

    model_config = SettingsConfigDict(
        # Pydantic-settings попытается загрузить файл по этому пути.
        # Если файла нет, ошибки не будет.
        env_file=ENV_FILE_PATH,
        extra='ignore'
    )

# Создаем один глобальный экземпляр настроек.
settings = Settings()

# Диагностический вывод, который показывает, что переменные не загружены,
# если .env или переменные окружения отсутствуют, но приложение не падает.
if settings.OPENAI_API_KEY is None:
    print("--- WARNING: OPENAI_API_KEY is not set. OpenAI API will not work. ---")
if settings.DATABASE_URL is None:
    print("--- WARNING: DATABASE_URL is not set. Database connection will not work. ---")

print("--- Configuration Loaded ---")