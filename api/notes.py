# file: api/notes.py

from fastapi import (APIRouter, Depends, HTTPException, status,
                     UploadFile, File, Form, Query)
from sqlalchemy.orm import Session
from typing import List, Optional

from db import crud, schemas, models
from db.database import get_db
from api.auth_dependency import get_current_user

# --- Правильные явные импорты экземпляров ---
from services import ai_processor, content_processor
from services.storage import file_storage
from services.vector_store import vector_store

router = APIRouter(prefix="/notes", tags=["Notes"])

@router.post("/new", response_model=schemas.Note, status_code=status.HTTP_201_CREATED)
def create_new_note(
    source_type: models.NoteType = Form(...),
    data: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Создает новую заметку из разных источников (текст, ссылка, аудио через Whisper, YouTube, PDF, DOCX).
    """
    title = "Новая заметка"
    structured_content = []
    source_uri = None
    text_for_vector = ""

    # --- Обработка файловых источников (если файл был передан) ---
    file_path = None
    if file and file.filename:
        file_path = file_storage.save_file(file)
        source_uri = file_storage.get_file_url(file_path)

    # --- Логика по типам ---
    if source_type == models.NoteType.TEXT:
        if not data:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Text data is required for type 'text'.")
        title = f"Текстовая заметка: {data[:30]}..."
        structured_content = [schemas.TextBlock(text=data)]
        text_for_vector = data
    elif source_type == models.NoteType.LINK:
        if not data:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "URL data is required for type 'link'.")
        source_uri = data
        extracted_text = content_processor.extract_text_from_link(data)
        title = f"Заметка из ссылки: {data[:40]}..."
        structured_content = [schemas.TextBlock(text=extracted_text)]
        text_for_vector = extracted_text
    elif source_type == models.NoteType.YOUTUBE:
        if not data:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "YouTube URL is required for type 'youtube'.")
        source_uri = data
        extracted_text = content_processor.get_text_from_youtube(data)
        if not extracted_text:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Could not get subtitles from YouTube video.")
        title = f"Заметка из YouTube: {data[:40]}..."
        structured_content = [schemas.TextBlock(text=extracted_text)]
        text_for_vector = extracted_text
    elif source_type == models.NoteType.PDF:
        if not file_path:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "PDF file is required for type 'pdf'.")
        extracted_text = content_processor.get_text_from_pdf(file_path)
        if not extracted_text:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Could not extract text from PDF file.")
        title = f"Заметка из PDF: {file.filename}"
        structured_content = [schemas.TextBlock(text=extracted_text)]
        text_for_vector = extracted_text
    elif source_type == models.NoteType.DOCX:
        if not file_path:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "DOCX file is required for type 'docx'.")
        extracted_text = content_processor.get_text_from_docx(file_path)
        if not extracted_text:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Could not extract text from DOCX file.")
        title = f"Заметка из DOCX: {file.filename}"
        structured_content = [schemas.TextBlock(text=extracted_text)]
        text_for_vector = extracted_text
    
    # --- ИЗМЕНЕННАЯ ЛОГИКА ДЛЯ АУДИО ---
    elif source_type == models.NoteType.AUDIO:
        if not file_path:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Audio file is required for type 'audio'.")
        
        # Используем новую функцию транскрибации через Whisper
        full_transcript = ai_processor.transcribe_audio_with_whisper(file_path)
        
        title = f"Транскрипция аудио: {file.filename}"
        # Сохраняем полный транскрипт как простой текст
        structured_content = [schemas.TextBlock(text=full_transcript)]
        text_for_vector = full_transcript
    
    # Мы убрали PHOTO, так как Google Vision больше не используется
    # Если нужно будет вернуть, можно будет добавить сюда
    else:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or unsupported source type.")

    # --- Сохранение результата ---
    note_to_create = schemas.NoteCreate(
        title=title,
        type=source_type,
        content=[item.model_dump() for item in structured_content],
        source_uri=source_uri
    )
    
    db_note = crud.create_note(db, note=note_to_create, user_id=current_user.id)
    
    if text_for_vector:
        vector_store.upsert_note(
            note_id=db_note.id,
            user_id=current_user.id,
            text_content=text_for_vector
        )
        
    return db_note


@router.get("/", response_model=List[schemas.Note])
def get_all_user_notes(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    return crud.get_all_notes_by_user(db=db, user_id=current_user.id)


@router.get("/search", response_model=List[schemas.Note])
def find_notes_by_semantic_search(
    q: str = Query(..., min_length=3, description="Поисковый запрос для семантического поиска"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if not q.strip():
        return []
    note_ids = vector_store.search_notes(user_id=current_user.id, query_text=q)
    if not note_ids:
        return []
    notes = db.query(models.Note).filter(models.Note.id.in_(note_ids)).all()
    notes_map = {note.id: note for note in notes}
    sorted_notes = [notes_map[id] for id in note_ids if id in notes_map]
    return sorted_notes