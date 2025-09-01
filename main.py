# file: main.py

import os
from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect, Query, status, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

# Импортируем наши модули и роутеры
from db.database import engine, get_db
from db import models, crud
# --- ИЗМЕНЕНИЕ 1: Убираем импорт `video` ---
from api import auth, folders, notes, ai_tasks, tiktok_video, chat

from api.connection_manager import manager
from api.auth_dependency import get_current_user


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
    swagger_ui_parameters={"persistAuthorization": True},
    swagger_ui_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui-bundle.js",
    swagger_ui_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui.css"
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
# --- ИЗМЕНЕНИЕ 2: Убираем подключение роутера `video` ---
# app.include_router(video.router)
app.include_router(ai_tasks.router)
app.include_router(tiktok_video.router)
app.include_router(chat.router)
print("--- REST API routers included ---")


# --- WebSocket Endpoint for Collaboration ---
@app.websocket("/ws/{note_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    note_id: str,
    token: str = Query(...),
):
    db = next(get_db())
    user = None
    try:
        user = get_current_user(token=token, db=db)
    
        if not user:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        note = crud.get_note_by_id(db, note_id=int(note_id), user_id=user.id)
        if not note:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        await manager.connect(websocket, note_id)
        print(f"WebSocket connection established for user {user.id} to note {note_id}")
        
        try:
            while True:
                data = await websocket.receive_text()
                await manager.broadcast(data, note_id, websocket)
        except WebSocketDisconnect:
            manager.disconnect(websocket, note_id)
            print(f"WebSocket connection closed for user {user.id} from note {note_id}")
            
    except HTTPException:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
    finally:
        db.close()


# --- Корневой эндпоинт ---
@app.get("/", tags=["Root"])
def read_root():
    return {"status": "ok", "message": "Welcome to AI Note Taker API v2.0!"}


print("--- main.py loaded successfully. Uvicorn will now start the server. ---")