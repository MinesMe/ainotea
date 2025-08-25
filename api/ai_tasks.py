# file: api/ai_tasks.py

from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlalchemy.orm import Session
from datetime import datetime

# Импортируем наши модули
from db import crud, schemas, models
from db.database import get_db
from api.auth_dependency import get_current_user
from services import ai_processor

# Создаем новый роутер для AI-задач
router = APIRouter(prefix="/ai", tags=["AI Tasks"])

@router.post("/generate", response_model=schemas.AIGeneratedContent)
async def generate_ai_content(
    note_id: int = Form(...),
    task_type: schemas.AITaskType = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Запускает генерацию AI-контента (summary, flashcards, quiz) для существующей заметки
    и сохраняет результат в базу данных.
    """
    # --- СИНХРОННЫЙ БЛОК: РАБОТА С БАЗОЙ ДАННЫХ ---
    # 1. Находим заметку в БД и проверяем, что она принадлежит текущему пользователю
    note = crud.get_note_by_id(db, note_id=note_id, user_id=current_user.id)
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found."
        )

    # 2. Собираем весь текст из контента заметки для отправки в AI
    text_content = ""
    if isinstance(note.content, list):
        text_content = " ".join([
            block.get("text", "") for block in note.content if isinstance(block, dict)
        ])
    
    if not text_content.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Note has no text content to process."
        )
    # --- КОНЕЦ СИНХРОННОГО БЛОКА ---

    # --- АСИНХРОННЫЙ БЛОК: РАБОТА С OpenAI ---
    generated_data = None
    if task_type == schemas.AITaskType.SUMMARY:
        generated_data = await ai_processor.generate_summary(text_content)
    elif task_type == schemas.AITaskType.FLASHCARDS:
        generated_data = await ai_processor.generate_flashcards(text_content)
    elif task_type == schemas.AITaskType.QUIZ:
        generated_data = await ai_processor.generate_quiz(text_content)
    
    if not generated_data or isinstance(generated_data, str): # Добавили проверку на строку (в случае ошибки)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate AI content from OpenAI. Reason: {generated_data}"
        )
    # --- КОНЕЦ АСИНХРОННОГО БЛОКА ---

    # --- СНОВА СИНХРОННЫЙ БЛОК: СОХРАНЕНИЕ В БД ---
    ai_content_to_create = schemas.AIGeneratedContentCreate(
        content_type=task_type,
        data=generated_data
    )
    
    # Сохраняем результат в базу данных с помощью новой CRUD-функции
    db_ai_content = crud.create_ai_content(db, content=ai_content_to_create, note_id=note.id)
    
    return db_ai_content