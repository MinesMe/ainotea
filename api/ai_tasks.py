# file: api/ai_tasks.py

from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlalchemy.orm import Session
from typing import Optional

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
    Запускает генерацию AI-контента (summary, flashcards, quiz)
    и сохраняет результат в базу данных.
    """
    # 1. Находим заметку в БД
    note = crud.get_note_by_id(db, note_id=note_id, user_id=current_user.id)
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found.")

    # 2. Собираем текст из заметки
    text_content = ""
    if isinstance(note.content, list):
        text_content = " ".join([block.get("text", "") for block in note.content if isinstance(block, dict)])
    
    if not text_content.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Note has no text content to process.")
    
    # 3. Выполняем AI-задачу
    generated_data = None
    content_type_str = task_type.value

    if task_type == schemas.AITaskType.SUMMARY:
        generated_data = await ai_processor.generate_summary(text_content)
    elif task_type == schemas.AITaskType.FLASHCARDS:
        generated_data = await ai_processor.generate_flashcards(text_content)
    elif task_type == schemas.AITaskType.QUIZ:
        generated_data = await ai_processor.generate_quiz(text_content)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported task type: {task_type.value}"
        )

    if not generated_data or isinstance(generated_data, str):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate AI content. Reason: {generated_data}"
        )
    
    # 4. Сохраняем результат в БД
    ai_content_to_create = schemas.AIGeneratedContentCreate(
        content_type=content_type_str,
        data=generated_data
    )
    
    db_ai_content = crud.create_ai_content(db, content=ai_content_to_create, note_id=note_id)
    
    return db_ai_content