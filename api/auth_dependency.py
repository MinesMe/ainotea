# file: api/auth_dependency.py

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from db import crud, models
from db.database import get_db
from core import security

# Создаем правильную схему HTTPBearer
bearer_scheme = HTTPBearer(auto_error=True)

def get_current_user(
    auth: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db)
) -> models.User:
    """
    Зависимость для получения текущего пользователя на основе JWT Bearer токена.
    """
    token = auth.credentials
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = security.decode_access_token(token)
    if payload is None:
        raise credentials_exception

    device_id: str = payload.get("sub")
    if device_id is None:
        raise credentials_exception

    user = crud.get_user_by_device_id(db, device_id=device_id)
    if user is None:
        raise credentials_exception

    return user