# file: db/schemas.py

from pydantic import BaseModel, Field
from typing import Optional, List, Union, Any
from datetime import datetime
from enum import Enum

# Импортируем наш Enum из моделей, чтобы использовать его и здесь
from .models import NoteType

# --- НОВЫЙ ENUM ДЛЯ ИСТОЧНИКОВ ТЕКСТА ---
class AddTextSourceType(str, Enum):
    """Перечисление для всех доступных источников добавления текста в заметку."""
    TEXT = "text"
    LINK = "link"
    YOUTUBE = "youtube"
    PDF = "pdf"
    DOCX = "docx"
    AUDIO = "audio"
    RECORD = "record"

# --- Вспомогательные схемы (без изменений) ---

class TextBlock(BaseModel):
    """Схема для одного блока текста с заголовками."""
    header: Optional[str] = None
    sub_header: Optional[str] = None
    text: str

class TranscriptBlock(BaseModel):
    """Схема для одного блока транскрипции аудио."""
    time_start: float
    text: str

# --- Схемы для Аутентификации (без изменений) ---

class UserCreate(BaseModel):
    """Схема для создания пользователя (регистрации)."""
    device_id: str

class User(BaseModel):
    """Схема для отображения информации о пользователе."""
    id: int
    device_id: str
    created_at: datetime
    class Config:
        from_attributes = True

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

class FolderUpdate(BaseModel):
    """Схема для обновления папки. Все поля опциональны."""
    name: Optional[str] = None

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
    content: Optional[List[Union[TextBlock, TranscriptBlock]]] = None
    source_uri: Optional[str] = None
    folder_id: Optional[int] = None

class NoteCreate(NoteBase):
    """Схема для создания заметки (используется внутри кода)."""
    pass

class NoteUpdate(BaseModel):
    """Схема для обновления заметки. Все поля опциональны."""
    title: Optional[str] = None
    folder_id: Optional[int] = Field(None, nullable=True)


class Note(NoteBase):
    """Схема для отображения полной информации о заметке."""
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True

# --- Схемы для AI-задач ---

class AITaskType(str, Enum):
    """
    Перечисление для всех доступных типов AI-задач.
    """
    SUMMARY = "summary"
    FLASHCARDS = "flashcards"
    QUIZ = "quiz"

class AIGeneratedContentBase(BaseModel):
    """Базовая схема для сгенерированного контента."""
    content_type: AITaskType
    data: Any

class AIGeneratedContentCreate(AIGeneratedContentBase):
    """Схема для сохранения сгенерированного контента в БД."""
    pass

class AIGeneratedContent(AIGeneratedContentBase):
    """Схема для отображения сгенерированного контента в ответе API."""
    id: int
    note_id: int
    created_at: datetime
    class Config:
        from_attributes = True

# --- Схемы для Видео (без изменений) ---

class VoiceName(str, Enum):
    """Перечисление доступных голосов для озвучки видео."""
    FEMALE_STANDARD = "ru-RU-Wavenet-D"
    MALE_STANDARD = "ru-RU-Wavenet-E"
    FEMALE_ALT = "ru-RU-Wavenet-A"
    MALE_ALT = "ru-RU-Wavenet-B"

class VideoRequest(BaseModel):
    """Схема для запроса на генерацию видео."""
    note_id: int
    voice_name: VoiceName = VoiceName.FEMALE_STANDARD

class VoiceSample(BaseModel):
    """Схема для описания одного примера голоса."""
    name: str
    url: str

class VideoResponse(BaseModel):
    """Схема для ответа с URL на сгенерированное видео."""
    video_url: str