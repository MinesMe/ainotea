# file: db/database.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Импортируем наш объект с настройками, чтобы взять URL базы данных
from core.config import settings

# Создаем "движок" SQLAlchemy.
# Он является точкой входа к базе данных и управляет пулом соединений.
# Мы используем URL из нашего файла конфигурации.
engine = create_engine(
    settings.DATABASE_URL,
    # Рекомендуется для серверных приложений, чтобы избежать проблем
    # с соединениями, которые закрылись по таймауту.
    pool_pre_ping=True
)

# Создаем "фабрику сессий". Каждая сессия, созданная с помощью SessionLocal,
# будет отдельным сеансом работы с базой данных.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Создаем базовый класс для наших декларативных моделей.
# Все наши классы-модели (User, Note, Folder) будут наследоваться от него.
Base = declarative_base()


# --- Зависимость для FastAPI ---
def get_db():
    """
    Функция-зависимость (dependency) для FastAPI.
    Она создает новую сессию для каждого входящего запроса,
    предоставляет ее эндпоинту и гарантированно закрывает после выполнения запроса.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()