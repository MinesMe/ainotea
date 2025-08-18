# file: db/models.py

import enum
from sqlalchemy import (Column, Integer, Text, JSON, Enum as SQLAlchemyEnum,
                        ForeignKey, TIMESTAMP, func, UniqueConstraint)
from sqlalchemy.orm import relationship

from .database import Base

class NoteType(str, enum.Enum):
    TEXT = "text"
    PHOTO = "photo"
    AUDIO = "audio"
    LINK = "link"
    YOUTUBE = "youtube"
    PDF = "pdf"
    DOCX = "docx"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Text, unique=True, index=True, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    notes = relationship("Note", back_populates="owner", cascade="all, delete-orphan")
    folders = relationship("Folder", back_populates="owner", cascade="all, delete-orphan")

class Folder(Base):
    __tablename__ = "folders"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(Text, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    owner = relationship("User", back_populates="folders")
    notes = relationship("Note", back_populates="folder")
    __table_args__ = (UniqueConstraint('user_id', 'name', name='_user_folder_uc'),)

class Note(Base):
    __tablename__ = "notes"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(Text, nullable=False)
    type = Column(SQLAlchemyEnum(NoteType), nullable=False)
    content = Column(JSON, nullable=True)
    source_uri = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    folder_id = Column(Integer, ForeignKey("folders.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    owner = relationship("User", back_populates="notes")
    folder = relationship("Folder", back_populates="notes")
    # --- ДОБАВЛЯЕМ СВЯЗЬ С НОВОЙ ТАБЛИЦЕЙ ---
    ai_content = relationship("AIGeneratedContent", back_populates="note", cascade="all, delete-orphan")

# --- НОВАЯ ТАБЛИЦА ДЛЯ ХРАНЕНИЯ AI-КОНТЕНТА ---
class AIGeneratedContent(Base):
    """Модель для хранения контента, сгенерированного ИИ (саммари, квизы и т.д.)."""
    __tablename__ = "ai_generated_content"

    id = Column(Integer, primary_key=True, index=True)
    # Связь с заметкой. ondelete="CASCADE" означает, что при удалении заметки
    # весь связанный с ней AI-контент также будет удален.
    note_id = Column(Integer, ForeignKey("notes.id", ondelete="CASCADE"), nullable=False)
    # Тип контента: 'summary', 'flashcards' или 'quiz'
    content_type = Column(Text, nullable=False)
    # Здесь будет храниться сам JSON-результат от OpenAI
    data = Column(JSON, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

    # Связь обратно к заметке
    note = relationship("Note", back_populates="ai_content")