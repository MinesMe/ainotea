import docx
import fitz
import os

# Импортируем наш рабочий модуль-помощник
from . import youtube_helper

def get_text_from_youtube(url: str):
    """
    Эта функция вызывается из notes.py.
    Она просто передает URL в наш отлаженный модуль youtube_helper.
    """
    print("--- content_processor: Вызываю youtube_helper.fetch_transcript ---")
    return youtube_helper.fetch_transcript(url)


def get_text_from_docx(file_path: str):
    """Извлекает текст из файла DOCX."""
    try:
        doc = docx.Document(file_path)
        full_text = [para.text for para in doc.paragraphs]
        return "\n".join(full_text)
    except Exception as e:
        print(f"Failed to process DOCX file at {file_path}: {e}")
        return None


def get_text_from_pdf(file_path: str):
    """Извлекает текст из PDF-файла."""
    try:
        doc = fitz.open(file_path)
        full_text = ""
        for page in doc:
            full_text += page.get_text()

        if len(full_text.strip()) < 100:
            print(f"PDF at {file_path} contains little or no extractable text.")
            return None

        return full_text
    except Exception as e:
        print(f"Failed to process PDF file at {file_path}: {e}")
        return None