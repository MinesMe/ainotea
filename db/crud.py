# file: db/crud.py

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from typing import List, Optional

from . import models, schemas

# --- Функции для работы с Пользователями (User) ---

def get_user_by_device_id(db: Session, device_id: str) -> Optional[models.User]:
    """Находит пользователя по его уникальному device_id."""
    return db.query(models.User).filter(models.User.device_id == device_id).first()

def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    """Создает нового пользователя в базе данных."""
    db_user = models.User(device_id=user.device_id)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# --- Функции для работы с Заметками (Note) ---

def get_note_by_id(db: Session, note_id: int, user_id: int) -> Optional[models.Note]:
    """Находит заметку по ID, но только если она принадлежит указанному пользователю."""
    return db.query(models.Note).filter(models.Note.id == note_id, models.Note.user_id == user_id).first()

def get_all_notes_by_user(db: Session, user_id: int) -> List[models.Note]:
    """Возвращает список всех заметок для указанного пользователя."""
    return db.query(models.Note).filter(models.Note.user_id == user_id).order_by(models.Note.updated_at.desc()).all()

def create_note(db: Session, note: schemas.NoteCreate, user_id: int) -> models.Note:
    """Создает новую заметку для пользователя."""
    db_note = models.Note(**note.model_dump(), user_id=user_id)
    db.add(db_note)
    db.commit()
    db.refresh(db_note)
    return db_note

def update_note(db: Session, note_id: int, user_id: int, note_update: schemas.NoteUpdate) -> Optional[models.Note]:
    """Обновляет заметку (название, папка) для пользователя."""
    db_note = get_note_by_id(db, note_id=note_id, user_id=user_id)
    if not db_note:
        return None
    
    update_data = note_update.model_dump(exclude_unset=True)

    if 'folder_id' in update_data:
        db_note.folder_id = update_data['folder_id']
    if 'title' in update_data:
        db_note.title = update_data['title']

    db.commit()
    db.refresh(db_note)
    return db_note

def append_text_block_to_note(db: Session, db_note: models.Note, text_block: schemas.TextBlock) -> models.Note:
    """Добавляет новый текстовый блок в content заметки."""
    if not db_note.content:
        db_note.content = []
    
    # Добавляем новый блок как словарь
    db_note.content.append(text_block.model_dump())
    
    # Явно указываем SQLAlchemy, что JSON-поле было изменено
    flag_modified(db_note, "content")
    
    db.commit()
    db.refresh(db_note)
    return db_note


def add_note_to_folder(db: Session, note_id: int, folder_id: int, user_id: int) -> Optional[models.Note]:
    """Добавляет заметку в папку, проверяя, что и папка, и заметка принадлежат пользователю."""
    db_note = get_note_by_id(db, note_id, user_id)
    db_folder = get_folder_by_id(db, folder_id, user_id)
    if db_note and db_folder:
        db_note.folder_id = folder_id
        db.commit()
        db.refresh(db_note)
        return db_note
    return None

def delete_note_by_id(db: Session, note_id: int, user_id: int) -> Optional[models.Note]:
    """Удаляет заметку по ID, если она принадлежит пользователю."""
    db_note = get_note_by_id(db, note_id=note_id, user_id=user_id)
    if db_note:
        db.delete(db_note)
        db.commit()
        return db_note
    return None

# --- Функции для работы с Папками (Folder) ---

def get_folder_by_id(db: Session, folder_id: int, user_id: int) -> Optional[models.Folder]:
    """Находит папку по ID, но только если она принадлежит указанному пользователю."""
    return db.query(models.Folder).filter(models.Folder.id == folder_id, models.Folder.user_id == user_id).first()

def get_all_folders_by_user(db: Session, user_id: int) -> List[models.Folder]:
    """Возвращает список всех папок для указанного пользователя."""
    return db.query(models.Folder).filter(models.Folder.user_id == user_id).order_by(models.Folder.name).all()

def create_folder(db: Session, folder: schemas.FolderCreate, user_id: int) -> models.Folder:
    """Создает новую папку для пользователя."""
    db_folder = models.Folder(name=folder.name, user_id=user_id)
    db.add(db_folder)
    db.commit()
    db.refresh(db_folder)
    return db_folder

def update_folder(db: Session, folder_id: int, user_id: int, folder_update: schemas.FolderUpdate) -> Optional[models.Folder]:
    """Обновляет название папки для пользователя."""
    db_folder = get_folder_by_id(db, folder_id=folder_id, user_id=user_id)
    if not db_folder:
        return None
    
    update_data = folder_update.model_dump(exclude_unset=True)
    if 'name' in update_data:
        db_folder.name = update_data['name']
    
    db.commit()
    db.refresh(db_folder)
    return db_folder

def delete_folder_by_id(db: Session, folder_id: int, user_id: int) -> Optional[models.Folder]:
    """Удаляет папку по ID, если она принадлежит пользователю."""
    db_folder = get_folder_by_id(db, folder_id=folder_id, user_id=user_id)
    if db_folder:
        db.delete(db_folder)
        db.commit()
        return db_folder
    return None

# --- Функция для сохранения AI-контента ---
def create_ai_content(db: Session, content: schemas.AIGeneratedContentCreate, note_id: int) -> models.AIGeneratedContent:
    """Сохраняет сгенерированный AI-контент в базу данных, привязывая его к заметке."""
    db_content = models.AIGeneratedContent(
        **content.model_dump(),
        note_id=note_id
    )
    db.add(db_content)
    db.commit()
    db.refresh(db_content)
    return db_content