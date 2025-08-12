# file: db/models.py

import enum
from sqlalchemy import (Column, Integer, Text, JSON, Enum as SQLAlchemyEnum,
                        ForeignKey, TIMESTAMP, func, UniqueConstraint)
from sqlalchemy.orm import relationship

# Импортируем наш базовый класс для моделей из database.py
from .database import Base

# Создаем Python Enum для типа заметки.
# Это обеспечит консистентность данных.
class NoteType(str, enum.Enum):
    TEXT = "text"
    PHOTO = "photo"
    AUDIO = "audio"
    LINK = "link"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Text, unique=True, index=True, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

    # Связи: один пользователь может иметь много заметок и папок.
    # cascade="all, delete-orphan" означает, что при удалении пользователя
    # все его заметки и папки также будут удалены.
    notes = relationship("Note", back_populates="owner", cascade="all, delete-orphan")
    folders = relationship("Folder", back_populates="owner", cascade="all, delete-orphan")


class Folder(Base):
    __tablename__ = "folders"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(Text, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

    # Связь с владельцем (пользователем)
    owner = relationship("User", back_populates="folders")
    # Связь с заметками в этой папке
    notes = relationship("Note", back_populates="folder")

    # Ограничение: у одного пользователя не может быть двух папок с одинаковым именем.
    __table_args__ = (UniqueConstraint('user_id', 'name', name='_user_folder_uc'),)


class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(Text, nullable=False)
    # Используем Enum, который мы определили выше
    type = Column(SQLAlchemyEnum(NoteType), nullable=False)
    # JSONB в PostgreSQL - мощный тип для хранения структурированных данных,
    # таких как транскрипты или результаты анализа текста.
    content = Column(JSON, nullable=True)
    # Здесь будет храниться ссылка на исходный файл (в облаке) или URL.
    source_uri = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    # ondelete="SET NULL" означает, что если папка будет удалена,
    # поле folder_id у заметки станет NULL, но сама заметка не удалится.
    folder_id = Column(Integer, ForeignKey("folders.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # Связи
    owner = relationship("User", back_populates="notes")
    folder = relationship("Folder", back_populates="notes")