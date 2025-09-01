# file: api/chat.py

from fastapi import APIRouter, Depends, HTTPException, status

# Импортируем все зависимости
from db import schemas, models
from api.auth_dependency import get_current_user
from services import ai_processor

# Создаем роутер для чата
router = APIRouter(prefix="/chat", tags=["Chat"])

@router.post("/", response_model=schemas.ChatResponse)
async def handle_chat(
    request: schemas.ChatRequest,
    current_user: models.User = Depends(get_current_user)
):
    """
    Принимает текстовое сообщение от пользователя и возвращает ответ от GPT.
    """
    # Вызываем функцию из нашего сервиса, передавая ей текст из запроса
    response_data = await ai_processor.get_gpt_chat_response(request.text)
    
    # Обрабатываем случай, если сервис вернул строку с ошибкой
    if isinstance(response_data, str):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=response_data
        )

    # Извлекаем ответ из словаря
    reply = response_data.get("reply")
    if not reply:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Received an empty reply from the AI service."
        )
        
    # Возвращаем данные в формате ChatResponse, как и обещали в декораторе
    return schemas.ChatResponse(reply=reply)