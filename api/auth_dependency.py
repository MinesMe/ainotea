# file: api/auth_dependency.py

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from db import crud, models
from db.database import get_db
from core import security

# Создаем схему аутентификации OAuth2.
# tokenUrl - это эндпоинт, где клиент может получить токен.
# В нашем случае, это /auth/signup. Это нужно в основном для документации Swagger.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/signup")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.User:
    """
    Зависимость для получения текущего пользователя на основе JWT токена.

    1. Принимает токен из заголовка Authorization: Bearer <token>.
    2. Декодирует токен.
    3. Извлекает из токена device_id (который мы положили в поле 'sub').
    4. Находит пользователя в базе данных по device_id.
    5. Возвращает объект пользователя или выбрасывает ошибку HTTP 401.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Декодируем токен
    payload = security.decode_access_token(token)
    if payload is None:
        # Если токен невалиден (просрочен, неверная подпись)
        raise credentials_exception

    # Извлекаем идентификатор пользователя (device_id) из поля 'sub'
    device_id: str = payload.get("sub")
    if device_id is None:
        raise credentials_exception

    # Находим пользователя в базе данных
    user = crud.get_user_by_device_id(db, device_id=device_id)
    if user is None:
        # Если пользователь с таким device_id (из токена) не найден в БД
        raise credentials_exception

    # Если все проверки пройдены, возвращаем объект пользователя
    return user