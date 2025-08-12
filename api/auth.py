# file: api/auth.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

# Импортируем наши модули
from db import crud, schemas
from db.database import get_db
from core import security

# Создаем новый роутер.
# prefix="/auth" означает, что все эндпоинты в этом файле будут начинаться с /auth
# tags=["Authentication"] группирует эти эндпоинты в документации Swagger
router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/signup", response_model=schemas.Token, status_code=status.HTTP_201_CREATED)
def signup_user(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    """
    Регистрирует нового пользователя по device_id или возвращает токен для существующего.
    Это реализация эндпоинта "signUp" из ТЗ.

    - **device_id**: Уникальный идентификатор устройства, который клиент будет хранить.
    """
    if not user_in.device_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Device ID is required."
        )

    # Проверяем, существует ли уже пользователь с таким device_id
    db_user = crud.get_user_by_device_id(db, device_id=user_in.device_id)

    # Если пользователя нет, создаем его
    if not db_user:
        db_user = crud.create_user(db, user=user_in)
        print(f"New user created with device_id: {db_user.device_id}")
    else:
        print(f"User with device_id {db_user.device_id} already exists. Issuing new token.")

    # Создаем JWT токен. В 'sub' (subject) мы помещаем device_id.
    # Это позволит нам в будущем идентифицировать пользователя по токену.
    access_token = security.create_access_token(
        data={"sub": db_user.device_id}
    )

    # Возвращаем токен клиенту
    return {"access_token": access_token, "token_type": "bearer"}