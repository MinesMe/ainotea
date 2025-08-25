# file: api/folders.py

from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from typing import List

# Импортируем наши модули
from db import crud, schemas, models
from db.database import get_db
from .auth_dependency import get_current_user

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
    existing_folders = {f.name for f in crud.get_all_folders_by_user(db, user_id=current_user.id)}
    if folder_in.name in existing_folders:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Папка с именем '{folder_in.name}' уже существует."
        )
    return crud.create_folder(db=db, folder=folder_in, user_id=current_user.id)

@router.get("/", response_model=List[schemas.Folder])
def get_all_user_folders(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Возвращает список всех папок, принадлежащих текущему пользователю.
    """
    return crud.get_all_folders_by_user(db=db, user_id=current_user.id)


@router.put("/{folder_id}", response_model=schemas.Folder)
def update_folder(
    folder_id: int,
    folder_update: schemas.FolderUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Обновляет папку по ее ID. Позволяет изменить название папки.
    """
    updated_folder = crud.update_folder(
        db, folder_id=folder_id, user_id=current_user.id, folder_update=folder_update
    )
    if not updated_folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Папка с ID {folder_id} не найдена."
        )
    return updated_folder

@router.delete("/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_folder(
    folder_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Удаляет папку по ее ID.
    Заметки из папки не удаляются, а открепляются от нее.
    """
    deleted_folder = crud.delete_folder_by_id(db, folder_id=folder_id, user_id=current_user.id)
    if not deleted_folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Папка с ID {folder_id} не найдена."
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{folder_id}/notes/{note_id}", response_model=schemas.Note)
def add_note_to_folder(
    folder_id: int,
    note_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Добавляет существующую заметку в существующую папку.
    """
    folder = crud.get_folder_by_id(db, folder_id=folder_id, user_id=current_user.id)
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Папка с ID {folder_id} не найдена."
        )
    note = crud.get_note_by_id(db, note_id=note_id, user_id=current_user.id)
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Заметка с ID {note_id} не найдена."
        )

    updated_note = crud.add_note_to_folder(db=db, note_id=note_id, folder_id=folder_id, user_id=current_user.id)
    return updated_note