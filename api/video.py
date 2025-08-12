# file: api/video.py

import os
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from db import crud, schemas, models
from db.database import get_db
from .auth_dependency import get_current_user
from services import video_generator

router = APIRouter(prefix="/video", tags=["Video Generation"])

# Путь к фоновому видео. Убедитесь, что этот файл существует в корне проекта.
BACKGROUND_VIDEO_PATH = "background.mp4"

@router.get("/voice-samples", response_model=List[schemas.VoiceSample])
def get_voice_samples():
    """
    Возвращает список доступных примеров голосов.
    В текущей реализации это просто заглушка.
    Для production здесь можно было бы заранее сгенерировать и сохранить
    несколько 5-секундных аудиофайлов.
    """
    # TODO: Реализовать генерацию и хранение реальных семплов.
    # Сейчас возвращаем статический список для примера.
    sample_voices = [
        {"name": "Стандартный женский", "voice_name": "ru-RU-Wavenet-D"},
        {"name": "Стандартный мужской", "voice_name": "ru-RU-Wavenet-E"},
        {"name": "Альтернативный женский", "voice_name": "ru-RU-Wavenet-A"},
        {"name": "Альтернативный мужской", "voice_name": "ru-RU-Wavenet-B"},
    ]
    # В реальном приложении URL будет указывать на статический файл.
    # Например: /static/voices/ru-RU-Wavenet-D.mp3
    return [
        schemas.VoiceSample(name=v["name"], url=f"placeholder_for_{v['voice_name']}")
        for v in sample_voices
    ]

@router.post("/create-from-note", response_model=schemas.VideoResponse)
def create_video_from_note(
    video_request: schemas.VideoRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Создает видео на основе текста заметки.
    Реализация эндпоинта "CreateTikTok" из ТЗ.
    """
    # 1. Проверяем, существует ли фоновое видео
    if not os.path.exists(BACKGROUND_VIDEO_PATH):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Background video not found at '{BACKGROUND_VIDEO_PATH}'."
        )

    # 2. Находим заметку в БД и проверяем, что она принадлежит пользователю
    note = crud.get_note_by_id(db, note_id=video_request.note_id, user_id=current_user.id)
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note with id {video_request.note_id} not found."
        )

    # 3. Собираем весь текст из контента заметки
    full_text = ""
    if note.content and isinstance(note.content, list):
        full_text = " ".join([block.get("text", "") for block in note.content])

    if not full_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Note has no text content to generate video from."
        )

    # 4. Запускаем процесс генерации видео
    try:
        final_video_path = video_generator.create_video_from_summary(
            summary_text=full_text,
            background_video_path=BACKGROUND_VIDEO_PATH,
            voice_name=video_request.voice_name
        )
        # Преобразуем путь к файлу в URL
        video_url = f"/{final_video_path}"
        return schemas.VideoResponse(video_url=video_url)

    except Exception as e:
        # Ловим любые ошибки в процессе генерации (от FFmpeg, Google TTS и т.д.)
        print(f"Error during video generation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during video generation: {str(e)}"
        )