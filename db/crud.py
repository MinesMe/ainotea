# file: db/crud.py

from sqlalchemy.orm import Session
from typing import List, Optional

# Импортируем наши модели (для запросов к БД) и схемы (для типизации)
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
    # .model_dump() преобразует Pydantic схему в словарь, готовый для SQLAlchemy
    db_note = models.Note(**note.model_dump(), user_id=user_id)
    db.add(db_note)
    db.commit()
    db.refresh(db_note)
    return db_note

def update_note_content(db: Session, note_id: int, title: str, content: list) -> Optional[models.Note]:
    """Обновляет заголовок и содержимое существующей заметки."""
    db_note = db.query(models.Note).filter(models.Note.id == note_id).first()
    if db_note:
        db_note.title = title
        db_note.content = [item.model_dump() for item in content] # Сохраняем как JSON
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