# file: db/schemas.py

from pydantic import BaseModel, Field
from typing import Optional, List, Union
from datetime import datetime

# Импортируем наш Enum из моделей, чтобы использовать его и здесь
from .models import NoteType

# --- Вспомогательные схемы для структурированного контента ---

class TextBlock(BaseModel):
    """Схема для одного блока текста с заголовками."""
    header: Optional[str] = None
    sub_header: Optional[str] = None
    text: str

class TranscriptBlock(BaseModel):
    """Схема для одного блока транскрипции аудио."""
    time_start: float
    text: str

# --- Схемы для Аутентификации ---

class UserCreate(BaseModel):
    """Схема для создания пользователя (регистрации)."""
    device_id: str

class User(BaseModel):
    """Схема для отображения информации о пользователе."""
    id: int
    device_id: str
    created_at: datetime

    class Config:
        from_attributes = True # Разрешает Pydantic читать данные из атрибутов объекта SQLAlchemy

class Token(BaseModel):
    """Схема для возврата JWT токена."""
    access_token: str
    token_type: str

# --- Схемы для Папок ---

class FolderBase(BaseModel):
    """Базовая схема для папки."""
    name: str

class FolderCreate(FolderBase):
    """Схема для создания папки (наследуется от базовой)."""
    pass

class Folder(FolderBase):
    """Схема для отображения папки."""
    id: int

    class Config:
        from_attributes = True

# --- Схемы для Заметок ---

class NoteBase(BaseModel):
    """Базовая схема для заметки, содержит общие поля."""
    title: str
    type: NoteType
    # content может быть списком, содержащим либо TextBlock, либо TranscriptBlock
    content: Optional[List[Union[TextBlock, TranscriptBlock]]] = None
    source_uri: Optional[str] = None
    folder_id: Optional[int] = None

class NoteCreate(NoteBase):
    """Схема для создания заметки (используется внутри кода, а не напрямую в API)."""
    pass

class NoteUpdate(BaseModel):
    """Схема для обновления заметки (например, для перемещения в папку)."""
    folder_id: Optional[int] = None

class Note(NoteBase):
    """Схема для отображения полной информации о заметке."""
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# --- Схемы для Видео ---

class VideoRequest(BaseModel):
    """Схема для запроса на генерацию видео."""
    note_id: int
    voice_name: str = "ru-RU-Wavenet-D" # Голос по умолчанию

class VoiceSample(BaseModel):
    """Схема для описания одного примера голоса."""
    name: str
    url: str

class VideoResponse(BaseModel):
    """Схема для ответа с URL на сгенерированное видео."""
    video_url: str