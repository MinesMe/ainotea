# file: api/tiktok_video.py

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import JSONResponse

from db import models
from api.auth_dependency import get_current_user
from services import dynamic_video_creator
from services.storage import file_storage # Используем для сохранения временного файла

router = APIRouter(prefix="/tiktok-video", tags=["TikTok Video Generation"])

@router.post("/create", status_code=status.HTTP_201_CREATED)
async def create_tiktok_style_video(
    text: str = Form(..., description="Текст, который будет озвучен и превращен в субтитры."),
    background_video: UploadFile = File(..., description="Фоновое видео в формате MP4."),
    current_user: models.User = Depends(get_current_user)
):
    """
    Создает видео в стиле TikTok с озвучкой и динамическими субтитрами.
    
    Этот эндпоинт объединяет функционал Продукта 1 (генератор видео)
    с архитектурой Продукта 2 (AI Notetaker).
    """
    if not background_video.content_type == "video/mp4":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный тип файла. Пожалуйста, загрузите видео в формате MP4."
        )

    try:
        # Сохраняем загруженное видео во временное место
        temp_video_path = file_storage.save_file(background_video)
        
        # Вызываем основной сервис для создания видео
        final_video_path = dynamic_video_creator.create_dynamic_subtitle_video(
            text=text,
            background_video_path=temp_video_path
        )
        
        # Преобразуем локальный путь в URL, который доступен клиенту
        video_url = f"/{final_video_path}"
        
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={"message": "Видео успешно создано!", "video_url": video_url}
        )
        
    except FileNotFoundError as e:
         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        print(f"Произошла ошибка при создании видео: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Произошла внутренняя ошибка при создании видео: {e}"
        )