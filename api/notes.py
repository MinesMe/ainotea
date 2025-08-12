# file: api/notes.py

from fastapi import (APIRouter, Depends, HTTPException, status,
                     UploadFile, File, Form, Query)
from sqlalchemy.orm import Session
from typing import List, Optional

from db import crud, schemas, models
from db.database import get_db
from .auth_dependency import get_current_user
from services import ai_processor, storage, vector_store

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
    Создает новую заметку из разных источников (текст, ссылка, фото, аудио).
    Реализация эндпоинта "NewNote" из ТЗ.
    """
    title = "Новая заметка"
    structured_content = []
    source_uri = None
    text_for_vector = ""

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

    elif source_type in [models.NoteType.PHOTO, models.NoteType.AUDIO]:
        if not file:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"File is required for type '{source_type.value}'.")
        
        file_path = storage.save_file(file)
        source_uri = storage.get_file_url(file_path)

        if source_type == models.NoteType.PHOTO:
            extracted_text = ai_processor.extract_text_from_photo(file_path)
            title, structured_content = ai_processor.summarize_and_structure_text(extracted_text, "photo")
            text_for_vector = extracted_text
        
        elif source_type == models.NoteType.AUDIO:
            full_transcript, transcript_blocks = ai_processor.transcribe_audio(file_path)
            title, _ = ai_processor.summarize_and_structure_text(full_transcript, "audio")
            structured_content = transcript_blocks # Для аудио сохраняем транскрипт
            text_for_vector = full_transcript

    else:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid source type.")

    # Создаем схему для новой заметки
    note_to_create = schemas.NoteCreate(
        title=title,
        type=source_type,
        content=[item.model_dump() for item in structured_content],
        source_uri=source_uri
    )
    
    # Сохраняем заметку в основной БД
    db_note = crud.create_note(db, note=note_to_create, user_id=current_user.id)

    # Добавляем/обновляем вектор заметки для поиска
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
    Реализация эндпоинта "GetAll notes" из ТЗ.
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
    Реализация эндпоинта "FindNote" из ТЗ.
    """
    if not q.strip():
        return []

    # Ищем ID релевантных заметок в векторном хранилище
    note_ids = vector_store.search_notes(user_id=current_user.id, query_text=q)

    if not note_ids:
        return []

    # Получаем полные объекты заметок из основной БД по найденным ID
    notes = db.query(models.Note).filter(models.Note.id.in_(note_ids)).all()
    
    # Сортируем результат в том же порядке, в котором их вернул векторный поиск
    notes_map = {note.id: note for note in notes}
    sorted_notes = [notes_map[id] for id in note_ids if id in notes_map]

    return sorted_notes