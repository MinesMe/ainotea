# file: api/notes.py

from fastapi import (APIRouter, Depends, HTTPException, status,
                     UploadFile, File, Form, Query, Response)
from sqlalchemy.orm import Session
from typing import List, Optional

# Импортируем все зависимости
from db import crud, schemas, models
from db.database import get_db
from api.auth_dependency import get_current_user
from services import content_processor, ai_processor
from services.storage import file_storage
from services.vector_store import vector_store
from services import url_reader_helper

router = APIRouter(prefix="/notes", tags=["Notes"])

# --- Внутренние функции-помощники ---

def _extract_text_from_source(
    source_type: schemas.AddTextSourceType,
    data: Optional[str] = None,
    file: Optional[UploadFile] = None
) -> str:
    """Извлекает текст из различных источников (текст, ссылка, файл)."""
    extracted_text = ""
    
    # --- Блок для источников, использующих 'data' (текст/ссылка) ---
    if source_type in [schemas.AddTextSourceType.TEXT, schemas.AddTextSourceType.LINK, schemas.AddTextSourceType.YOUTUBE]:
        if not data:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Для этого типа источника необходимо поле 'data'.")
        if source_type == schemas.AddTextSourceType.TEXT:
            extracted_text = data
        elif source_type == schemas.AddTextSourceType.LINK:
            extracted_text = url_reader_helper.get_text_from_url(data)
        elif source_type == schemas.AddTextSourceType.YOUTUBE:
            extracted_text = content_processor.get_text_from_youtube(data)

    # --- Блок для источников, использующих 'file' ---
    elif source_type in [schemas.AddTextSourceType.PDF, schemas.AddTextSourceType.DOCX, schemas.AddTextSourceType.AUDIO, schemas.AddTextSourceType.RECORD]:
        # 👇 ИЗМЕНЕНИЕ ЗДЕСЬ: Проверяем не только 'file', но и 'file.filename'
        if not file or not file.filename:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Для этого типа источника необходимо прикрепить файл.")
        
        file_path = file_storage.save_file(file)
        if source_type == schemas.AddTextSourceType.PDF:
            extracted_text = content_processor.get_text_from_pdf(file_path)
        elif source_type == schemas.AddTextSourceType.DOCX:
            extracted_text = content_processor.get_text_from_docx(file_path)
        elif source_type in [schemas.AddTextSourceType.AUDIO, schemas.AddTextSourceType.RECORD]:
            extracted_text = ai_processor.transcribe_audio_with_whisper(file_path)

    if not extracted_text or not extracted_text.strip():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Не удалось извлечь текст из источника типа '{source_type.value}'.")
        
    return extracted_text


def _create_and_save_note(
    db: Session, user: models.User, title: str, source_type: models.NoteType,
    structured_content: list, text_for_vector: str, source_uri: Optional[str] = None
) -> models.Note:
    """Внутренняя функция, которая создает, сохраняет и векторизует заметку."""
    note_to_create = schemas.NoteCreate(
        title=title, type=source_type, content=[item.model_dump() for item in structured_content],
        source_uri=source_uri
    )
    db_note = crud.create_note(db, note=note_to_create, user_id=user.id)
    if text_for_vector:
        vector_store.upsert_note_chunks(
            note_id=db_note.id, user_id=user.id, text_content=text_for_vector
        )
    return db_note

# --- ЭНДПОИНТЫ CRUD ---

@router.post("/new/from_data", response_model=schemas.Note, status_code=status.HTTP_201_CREATED)
def create_note_from_data(
    source_type: models.NoteType = Form(...),
    data: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Создает новую заметку из текста, обычной ссылки или YouTube URL."""
    add_text_source_type = schemas.AddTextSourceType(source_type.value)
    extracted_text = _extract_text_from_source(source_type=add_text_source_type, data=data)
    
    title_map = {
        models.NoteType.TEXT: f"Текстовая заметка: {data[:30]}...",
        models.NoteType.LINK: f"Заметка с веб-страницы: {data[:40]}...",
        models.NoteType.YOUTUBE: f"Заметка из YouTube: {data[:40]}...",
    }
    title = title_map.get(source_type)
    source_uri = data if source_type != models.NoteType.TEXT else None

    return _create_and_save_note(
        db, current_user, title, source_type, 
        [schemas.TextBlock(text=extracted_text)], extracted_text, source_uri
    )

@router.post("/new/from_file", response_model=schemas.Note, status_code=status.HTTP_201_CREATED)
def create_note_from_file(
    source_type: models.NoteType = Form(...), 
    file: UploadFile = File(...),
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    """Создает новую заметку из загруженного файла (PDF, DOCX, аудио)."""
    add_text_source_type = schemas.AddTextSourceType(source_type.value)
    extracted_text = _extract_text_from_source(source_type=add_text_source_type, file=file)
    
    title = f"Заметка из файла: {file.filename}"
    source_uri = file_storage.get_file_url(file_storage.get_path_from_filename(file.filename))

    return _create_and_save_note(
        db, current_user, title, source_type, 
        [schemas.TextBlock(text=extracted_text)], extracted_text, source_uri
    )

@router.post("/{note_id}/add-text", response_model=schemas.Note)
def add_text_to_note(
    note_id: int,
    source_type: schemas.AddTextSourceType = Form(...),
    data: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Добавляет новый текстовый блок в существующую заметку из источника."""
    db_note = crud.get_note_by_id(db, note_id=note_id, user_id=current_user.id)
    if not db_note:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Заметка с ID {note_id} не найдена.")

    extracted_text = _extract_text_from_source(source_type=source_type, data=data, file=file)
    new_text_block = schemas.TextBlock(
        header=f"Добавлено из '{source_type.value}'",
        text=extracted_text
    )

    updated_note = crud.append_text_block_to_note(db, db_note=db_note, text_block=new_text_block)
    
    full_text_content = " ".join([block.get("text", "") for block in updated_note.content if isinstance(block, dict)])
    vector_store.delete_note(note_id=note_id)
    vector_store.upsert_note_chunks(
        note_id=note_id, user_id=current_user.id, text_content=full_text_content
    )
    
    return updated_note


@router.get("/", response_model=List[schemas.Note])
def get_all_user_notes(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Возвращает список всех заметок текущего пользователя."""
    return crud.get_all_notes_by_user(db=db, user_id=current_user.id)

@router.put("/{note_id}", response_model=schemas.Note)
def update_note(
    note_id: int,
    note_update: schemas.NoteUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Обновляет название и/или папку заметки."""
    if note_update.folder_id is not None:
        folder = crud.get_folder_by_id(db, folder_id=note_update.folder_id, user_id=current_user.id)
        if not folder:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Папка с ID {note_update.folder_id} не найдена.")

    updated_note = crud.update_note(db, note_id=note_id, user_id=current_user.id, note_update=note_update)
    if not updated_note:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Заметка с ID {note_id} не найдена.")
    return updated_note

@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Удаляет заметку, а также все связанные с ней векторные данные."""
    vector_store.delete_note(note_id=note_id)
    deleted_note = crud.delete_note_by_id(db, note_id=note_id, user_id=current_user.id)
    if not deleted_note:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Заметка с ID {note_id} не найдена.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# --- ЭНДПОИНТ ДЛЯ ПОИСКА ---

@router.get("/search", response_model=List[schemas.Note])
def find_notes_by_semantic_search(
    q: str = Query(..., min_length=3, description="Поисковый запрос для семантического поиска"),
    db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    """Выполняет качественный семантический поиск по содержимому заметок."""
    if not q.strip(): return []
    search_results = vector_store.search_notes(user_id=current_user.id, query_text=q)
    if not search_results: return []
    
    ordered_unique_ids = []
    for res in search_results:
        if res['note_id'] not in ordered_unique_ids:
            ordered_unique_ids.append(res['note_id'])
            
    notes = db.query(models.Note).filter(models.Note.id.in_(ordered_unique_ids)).all()
    notes_map = {note.id: note for note in notes}
    sorted_notes = [notes_map[id] for id in ordered_unique_ids if id in notes_map]
    return sorted_notes