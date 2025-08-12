# file: main.py

import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Импортируем наши модули и роутеры
from db.database import engine
from db import models
from api import auth, folders, notes, video

# --- Инициализация ---

# 1. Создаем таблицы в базе данных на основе наших моделей.
# Если таблицы уже существуют, эта команда ничего не сделает.
models.Base.metadata.create_all(bind=engine)

# 2. Создаем основной объект приложения FastAPI
app = FastAPI(
    title="AI Note Taker API",
    description="Бэкэнд для умного приложения по ведению заметок.",
    version="1.0.0",
)

# 3. Создание директорий для статических файлов при запуске.
# Этот код выполняется каждый раз при старте приложения.
# os.makedirs() безопасно создает папки и не выдает ошибку, если они уже существуют.
os.makedirs("uploads", exist_ok=True)
os.makedirs("generated_videos", exist_ok=True)


# --- Настройка Middleware ---

# Настраиваем CORS (Cross-Origin Resource Sharing).
# Это позволяет фронтенд-приложениям, запущенным на других адресах,
# отправлять запросы к нашему API.
origins = [
    "http://localhost",
    "http://localhost:3000", # Для React по умолчанию
    "http://localhost:5173", # Для Vite (Vue, React) по умолчанию
    "http://localhost:8080", # Для Vue по умолчанию
    "*" # Разрешает все источники (можно использовать для простоты)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Разрешает все методы (GET, POST, и т.д.)
    allow_headers=["*"], # Разрешает все заголовки
)


# --- Монтирование статических директорий ---

# Этот код делает содержимое папок `uploads` и `generated_videos`
# доступным по URL. Например, файл ./uploads/image.jpg будет доступен
# по адресу <ваш_домен>/uploads/image.jpg
# Этот код теперь не будет вызывать ошибку, так как папки уже созданы.
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/generated_videos", StaticFiles(directory="generated_videos"), name="videos")


# --- Подключение роутеров ---

# Подключаем все наши эндпоинты из папки /api к основному приложению.
app.include_router(auth.router)
app.include_router(folders.router)
app.include_router(notes.router)
app.include_router(video.router)


# --- Корневой эндпоинт ---

@app.get("/", tags=["Root"])
def read_root():
    """
    Корневой эндпоинт для простой проверки, что API запущено и работает.
    """
    return {"status": "ok", "message": "Welcome to AI Note Taker API!"}