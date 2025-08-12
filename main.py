# file: main.py

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Импортируем наши модули и роутеры
from db.database import engine
from db import models
from api import auth, folders, notes, video

# --- Инициализация ---

# Создаем таблицы в базе данных на основе наших моделей.
# Если таблицы уже существуют, эта команда ничего не сделает.
models.Base.metadata.create_all(bind=engine)

# Создаем основной объект приложения FastAPI
app = FastAPI(
    title="AI Note Taker API",
    description="Бэкэнд для умного приложения по ведению заметок.",
    version="1.0.0",
)

# --- Настройка Middleware ---

# Настраиваем CORS (Cross-Origin Resource Sharing).
# origins = ["*"] позволяет принимать запросы с любого домена.
# Для production лучше указать конкретный домен вашего фронтенда.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Монтирование статических директорий ---

# Это позволит FastAPI раздавать файлы, которые мы генерируем или загружаем.
# Запрос на /uploads/filename.jpg будет искать файл в папке ./uploads/filename.jpg
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/generated_videos", StaticFiles(directory="generated_videos"), name="videos")
# Можно добавить и папку для примеров голосов
# app.mount("/static", StaticFiles(directory="static"), name="static")


# --- Подключение роутеров ---

# Подключаем все наши роутеры к основному приложению.
# Теперь все эндпоинты из auth.py будут доступны по адресу /auth/...
# все из notes.py - по адресу /notes/... и так далее.
app.include_router(auth.router)
app.include_router(folders.router)
app.include_router(notes.router)
app.include_router(video.router)


# --- Корневой эндпоинт ---

@app.get("/", tags=["Root"])
def read_root():
    """
    Корневой эндпоинт для проверки работоспособности API.
    """
    return {"status": "ok", "message": "Welcome to AI Note Taker API!"}