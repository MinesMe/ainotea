# file: api/notes.py

from fastapi import (APIRouter, Depends, HTTPException, status,
                     UploadFile, File, Form, Query)
from sqlalchemy.orm import Session
from typing import List, Optional, Union # <-- ДОБАВЛЕН UNION

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
    # --- ИСПРАВЛЕНИЕ: Разрешаем принимать либо файл, либо строку ---
    file: Optional[Union[UploadFile, str]] = File(None),
    # -----------------------------------------------------------
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Создает новую заметку из разных источников (текст, ссылка, фото, аудио, YouTube, PDF, DOCX).
    """
    title = "Новая заметка"
    structured_content = []
    source_uri = None
    text_for_vector = ""

    # --- ИСПРАВЛЕНИЕ: Улучшенная обработка файла ---
    file_path = None
    # Проверяем, что 'file' - это действительно объект файла И у него есть имя.
    # Это отсеет и пустые строки от Swagger, и "пустые" загрузки файлов.
    if isinstance(file, UploadFile) and file.filename:
        file_path = file_storage.save_file(file)
        source_uri = file_storage.get_file_url(file_path)
    # ---------------------------------------------

    # --- Логика по типам ---
    if source_type == models.NoteType.TEXT:
        if not data:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Text data is required for type 'text'.")
        title, structured_content = ai_processor.summarize_and_structure_text(data, "text")
        text_for_vector = data
    elif source_type == models.NoteType.LINK:
        if not data:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "URL data is required for type 'link'.")
        source_uri = data
        extracted_text = ai_processor.extract_text_from_link(data)
        title, structured_content = ai_processor.summarize_and_structure_text(extracted_text, "link")
        text_for_vector = extracted_text
    elif source_type == models.NoteType.YOUTUBE:
        if not data:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "YouTube URL is required for type 'youtube'.")
        source_uri = data
        extracted_text = content_processor.get_text_from_youtube(data)
        if not extracted_text:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Could not get subtitles from YouTube video.")
        title, structured_content = ai_processor.summarize_and_structure_text(extracted_text, "youtube")
        text_for_vector = extracted_text
    elif source_type == models.NoteType.PDF:
        if not file_path:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "PDF file is required for type 'pdf'.")
        extracted_text = content_processor.get_text_from_pdf(file_path)
        if not extracted_text:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Could not extract text from PDF file.")
        title, structured_content = ai_processor.summarize_and_structure_text(extracted_text, "pdf")
        text_for_vector = extracted_text
    elif source_type == models.NoteType.DOCX:
        if not file_path:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "DOCX file is required for type 'docx'.")
        extracted_text = content_processor.get_text_from_docx(file_path)
        if not extracted_text:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Could not extract text from DOCX file.")
        title, structured_content = ai_processor.summarize_and_structure_text(extracted_text, "docx")
        text_for_vector = extracted_text
    elif source_type == models.NoteType.PHOTO:
        if not file_path:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Photo file is required for type 'photo'.")
        extracted_text = ai_processor.extract_text_from_photo(file_path)
        title, structured_content = ai_processor.summarize_and_structure_text(extracted_text, "photo")
        text_for_vector = extracted_text
    elif source_type == models.NoteType.AUDIO:
        if not file_path:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Audio file is required for type 'audio'.")
        full_transcript, transcript_blocks = ai_processor.transcribe_audio(file_path)
        title, _ = ai_processor.summarize_and_structure_text(full_transcript, "audio")
        structured_content = transcript_blocks
        text_for_vector = full_transcript
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
    """
    Возвращает список всех заметок текущего пользователя.
    """
    return crud.get_all_notes_by_user(db=db, user_id=current_user.id)


@router.get("/search", response_model=List[schemas.Note])
def find_notes_by_semantic_search(
    q: str = Query(..., min_length=3, description="Поисковый запрос для семантического поиска"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Выполняет семантический ("умный") поиск по всем заметкам пользователя.
    """
    if not q.strip():
        return []

    note_ids = vector_store.search_notes(user_id=current_user.id, query_text=q)

    if not note_ids:
        return []

    notes = db.query(models.Note).filter(models.Note.id.in_(note_ids)).all()
    
    notes_map = {note.id: note for note in notes}
    sorted_notes = [notes_map[id] for id in note_ids if id in notes_map]

    return sorted_notes