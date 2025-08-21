# file: api/notes.py

from fastapi import (APIRouter, Depends, HTTPException, status,
                     UploadFile, File, Form, Query)
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

# Импортируем все необходимые модули и зависимости
from db import crud, schemas, models
from db.database import get_db
from api.auth_dependency import get_current_user
from services import content_processor, ai_processor
from services.storage import file_storage
from services.vector_store import vector_store
from services import url_reader_helper

# Создаем роутер для всех эндпоинтов, связанных с заметками
router = APIRouter(prefix="/notes", tags=["Notes"])


# --- ВНУТРЕННЯЯ ФУНКЦИЯ-ПОМОЩНИК, ЧТОБЫ НЕ ДУБЛИРОВАТЬ КОД ---
def _create_and_save_note(
    db: Session,
    user: models.User,
    title: str,
    source_type: models.NoteType,
    structured_content: list,
    text_for_vector: str,
    source_uri: Optional[str] = None
) -> models.Note:
    """
    Внутренняя функция, которая создает заметку в основной БД,
    а затем разбивает ее текст на чанки и сохраняет в векторной БД.
    """
    note_to_create = schemas.NoteCreate(
        title=title,
        type=source_type,
        content=[item.model_dump() for item in structured_content],
        source_uri=source_uri
    )
    # 1. Создаем заметку в основной базе (PostgreSQL/SQLite)
    db_note = crud.create_note(db, note=note_to_create, user_id=user.id)
    
    # 2. Если есть текст, вызываем новую функцию для чанкинга и сохранения в векторной базе
    if text_for_vector:
        vector_store.upsert_note_chunks(
            note_id=db_note.id,
            user_id=user.id,
            text_content=text_for_vector
        )
    return db_note


# --- ЭНДПОИНТ №1: ДЛЯ ТЕКСТА И ССЫЛОК (БЕЗ ФАЙЛОВ) ---

class NoteFromDataRequest(BaseModel):
    """Модель для запросов, не требующих загрузки файла. Принимает JSON."""
    source_type: models.NoteType
    data: str

@router.post("/new/from_data", response_model=schemas.Note, status_code=status.HTTP_201_CREATED)
def create_note_from_data(
    request_body: NoteFromDataRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Создает новую заметку из текста, обычной ссылки или YouTube URL."""
    source_type = request_body.source_type
    data = request_body.data
    
    # Проверяем, что тип источника подходит для этого эндпоинта
    if source_type not in [models.NoteType.TEXT, models.NoteType.LINK, models.NoteType.YOUTUBE]:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Этот эндпоинт поддерживает только типы 'text', 'link', 'youtube'.")

    if source_type == models.NoteType.TEXT:
        title = f"Текстовая заметка: {data[:30]}..."
        structured_content = [schemas.TextBlock(text=data)]
        text_for_vector = data
        source_uri = None

    elif source_type == models.NoteType.LINK:
        title = f"Заметка с веб-страницы: {data[:40]}..."
        extracted_text = url_reader_helper.get_text_from_url(data)
        if not extracted_text:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Не удалось извлечь текст с веб-страницы.")
        structured_content = [schemas.TextBlock(text=extracted_text)]
        text_for_vector = extracted_text
        source_uri = data

    elif source_type == models.NoteType.YOUTUBE:
        title = f"Заметка из YouTube: {data[:40]}..."
        extracted_text = content_processor.get_text_from_youtube(data)
        if not extracted_text:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Не удалось получить субтитры из YouTube видео.")
        structured_content = [schemas.TextBlock(text=extracted_text)]
        text_for_vector = extracted_text
        source_uri = data

    # Вызываем нашу внутреннюю функцию для создания и сохранения заметки
    return _create_and_save_note(db, current_user, title, source_type, structured_content, text_for_vector, source_uri)


# --- ЭНДПОИНТ №2: ДЛЯ ФАЙЛОВ (PDF, DOCX, АУДИО) ---

@router.post("/new/from_file", response_model=schemas.Note, status_code=status.HTTP_201_CREATED)
def create_note_from_file(
    source_type: models.NoteType = Form(...),
    file: UploadFile = File(...), # Файл здесь ОБЯЗАТЕЛЕН
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Создает новую заметку из загруженного файла (PDF, DOCX, аудио)."""
    if source_type not in [models.NoteType.PDF, models.NoteType.DOCX, models.NoteType.AUDIO, models.NoteType.RECORD]:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Этот эндпоинт поддерживает только типы 'pdf', 'docx', 'audio', 'record'.")

    file_path = file_storage.save_file(file)
    source_uri = file_storage.get_file_url(file_path)

    if source_type == models.NoteType.PDF:
        extracted_text = content_processor.get_text_from_pdf(file_path)
        if not extracted_text:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Не удалось извлечь текст из PDF файла.")
        title = f"Заметка из PDF: {file.filename}"
        structured_content = [schemas.TextBlock(text=extracted_text)]
        text_for_vector = extracted_text

    elif source_type == models.NoteType.DOCX:
        extracted_text = content_processor.get_text_from_docx(file_path)
        if not extracted_text:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Не удалось извлечь текст из DOCX файла.")
        title = f"Заметка из DOCX: {file.filename}"
        structured_content = [schemas.TextBlock(text=extracted_text)]
        text_for_vector = extracted_text
    
    elif source_type in [models.NoteType.AUDIO, models.NoteType.RECORD]:
        full_transcript = ai_processor.transcribe_audio_with_whisper(file_path)
        title = f"Транскрипция аудио: {file.filename}"
        structured_content = [schemas.TextBlock(text=full_transcript)]
        text_for_vector = full_transcript

    # Вызываем нашу внутреннюю функцию для создания и сохранения заметки
    return _create_and_save_note(db, current_user, title, source_type, structured_content, text_for_vector, source_uri)


# --- ЭНДПОИНТ №3: ПОЛУЧЕНИЕ ВСЕХ ЗАМЕТОК ---

@router.get("/", response_model=List[schemas.Note])
def get_all_user_notes(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Возвращает список всех заметок текущего пользователя."""
    return crud.get_all_notes_by_user(db=db, user_id=current_user.id)


# --- ЭНДПОИНТ №4: СЕМАНТИЧЕСКИЙ ПОИСК ---

@router.get("/search", response_model=List[schemas.Note])
def find_notes_by_semantic_search(
    q: str = Query(..., min_length=3, description="Поисковый запрос для семантического поиска"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Выполняет качественный семантический поиск по содержимому заметок."""
    if not q.strip():
        return []
    
    # 1. Ищем релевантные чанки в векторной базе
    search_results = vector_store.search_notes(user_id=current_user.id, query_text=q)
    if not search_results:
        return []
    
    # 2. Собираем уникальные ID родительских заметок в порядке релевантности
    ordered_unique_ids = []
    for res in search_results:
        if res['note_id'] not in ordered_unique_ids:
            ordered_unique_ids.append(res['note_id'])
            
    # 3. Получаем полные данные этих заметок из основной БД
    notes = db.query(models.Note).filter(models.Note.id.in_(ordered_unique_ids)).all()
    
    # 4. Сортируем полученные заметки в том порядке, в котором их вернул поиск
    notes_map = {note.id: note for note in notes}
    sorted_notes = [notes_map[id] for id in ordered_unique_ids if id in notes_map]
    
    return sorted_notes