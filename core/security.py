# file: core/security.py

from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from passlib.context import CryptContext

# Импортируем наш объект с настройками
from .config import settings

# Создаем контекст для хеширования паролей.
# Хоть в текущем ТЗ нет паролей, это хорошая практика на будущее,
# если вы решите добавить аутентификацию по email/паролю.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(data: dict) -> str:
    """
    Генерирует новый JWT токен доступа.

    :param data: Словарь с данными для включения в токен (например, {'sub': user_device_id}).
    :return: Строка с закодированным JWT токеном.
    """
    to_encode = data.copy()
    # Устанавливаем срок жизни токена
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})

    # Кодируем токен с использованием секрета и алгоритма из настроек
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict | None:
    """
    Декодирует JWT токен и возвращает его полезную нагрузку (payload).

    :param token: JWT токен в виде строки.
    :return: Словарь с данными из токена или None в случае ошибки.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        # Если токен невалиден (истек срок, неверная подпись), возвращаем None
        return None