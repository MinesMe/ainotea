# file: api/folders.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

# Импортируем наши модули
from db import crud, schemas, models
from db.database import get_db
from .auth_dependency import get_current_user # Мы создадим этот файл следующим

router = APIRouter(prefix="/folders", tags=["Folders"])

@router.post("/", response_model=schemas.Folder, status_code=status.HTTP_201_CREATED)
def create_new_folder(
    folder_in: schemas.FolderCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Создает новую папку для текущего пользователя.
    """
    return crud.create_folder(db=db, folder=folder_in, user_id=current_user.id)

@router.get("/", response_model=List[schemas.Folder])
def get_all_user_folders(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Возвращает список всех папок, принадлежащих текущему пользователю.
    Реализация эндпоинта "GetAll folders" из ТЗ.
    """
    return crud.get_all_folders_by_user(db=db, user_id=current_user.id)

@router.post("/{folder_id}/notes/{note_id}", response_model=schemas.Note)
def add_note_to_folder(
    folder_id: int,
    note_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Добавляет существующую заметку в существующую папку.
    Проверяет, что и заметка, и папка принадлежат текущему пользователю.
    Реализация эндпоинта "AddToFolder" из ТЗ.
    """
    # Проверяем, существует ли папка и принадлежит ли она пользователю
    folder = crud.get_folder_by_id(db, folder_id=folder_id, user_id=current_user.id)
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Folder with id {folder_id} not found."
        )

    # Проверяем, существует ли заметка и принадлежит ли она пользователю
    note = crud.get_note_by_id(db, note_id=note_id, user_id=current_user.id)
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note with id {note_id} not found."
        )

    # Выполняем операцию
    updated_note = crud.add_note_to_folder(db=db, note_id=note_id, folder_id=folder_id, user_id=current_user.id)
    if not updated_note:
        # Эта ошибка может возникнуть в редких случаях, если что-то пошло не так
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not add note to folder."
        )

    return updated_note