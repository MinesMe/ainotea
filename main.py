# file: main.py

# --- ДИАГНОСТИЧЕСКИЙ ВЫВОД ---
print("--- Starting main.py ---")

import os
from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect, Query, status
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

# Импортируем наши модули и роутеры
from db.database import engine, get_db
from db import models, crud
from api import auth, folders, notes, video, ai_tasks

# --- НОВЫЕ ИМПОРТЫ ДЛЯ WEBSOCKET ---
from api.connection_manager import manager
from api.auth_dependency import get_current_user # Нам нужна эта функция для проверки токена
# ------------------------------------


# --- Инициализация ---
print("--- Initializing application ---")

# 1. Создаем таблицы в базе данных
try:
    models.Base.metadata.create_all(bind=engine)
    print("--- Database tables checked/created successfully ---")
except Exception as e:
    print(f"--- CRITICAL: Failed to connect to database or create tables. Error: {e} ---")

# 2. Создаем основной объект приложения FastAPI
app = FastAPI(
    title="AI Note Taker API",
    description="Бэкэнд для умного приложения по ведению заметок с функциями OpenAI.",
    version="2.0.0",
)

# 3. Создание директорий для статических файлов
os.makedirs("uploads", exist_ok=True)
os.makedirs("generated_videos", exist_ok=True)
print("--- Static directories checked/created ---")


# --- Настройка Middleware ---
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
print("--- CORS middleware configured ---")


# --- Монтирование статических директорий ---
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/generated_videos", StaticFiles(directory="generated_videos"), name="videos")
print("--- Static routes mounted ---")


# --- Подключение REST API роутеров ---
app.include_router(auth.router)
app.include_router(folders.router)
app.include_router(notes.router)
app.include_router(video.router)
app.include_router(ai_tasks.router)
print("--- REST API routers included ---")


# --- WebSocket Endpoint for Collaboration ---
@app.websocket("/ws/{note_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    note_id: str,
    token: str = Query(...),
    db: Session = Depends(get_db) # FastAPI не может использовать Depends в WS, но мы вызовем его вручную
):
    """
    Эндпоинт для совместного редактирования заметки в реальном времени.
    """
    # Шаг 1: Аутентификация пользователя по токену из query-параметра
    user = None
    try:
        # Мы не можем использовать Depends(get_current_user) напрямую в WebSocket,
        # поэтому вызываем функцию get_current_user вручную.
        user = get_current_user(token=token, db=db)
    except HTTPException:
        # Если токен невалиден, get_current_user вызовет HTTPException
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Шаг 2: Проверка, что заметка существует и принадлежит пользователю
    note = crud.get_note_by_id(db, note_id=int(note_id), user_id=user.id)
    if not note:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Шаг 3: Подключение к "комнате" для этой заметки
    await manager.connect(websocket, note_id)
    print(f"WebSocket connection established for user {user.id} to note {note_id}")
    try:
        # Шаг 4: Бесконечный цикл для приема и отправки сообщений
        while True:
            data = await websocket.receive_text()
            # Рассылаем полученные данные всем остальным участникам в "комнате"
            await manager.broadcast(data, note_id, websocket)
    except WebSocketDisconnect:
        # Шаг 5: Отключение при разрыве соединения
        manager.disconnect(websocket, note_id)
        print(f"WebSocket connection closed for user {user.id} from note {note_id}")


# --- Корневой эндпоинт ---
@app.get("/", tags=["Root"])
def read_root():
    return {"status": "ok", "message": "Welcome to AI Note Taker API v2.0!"}


print("--- main.py loaded successfully. Uvicorn will now start the server. ---")