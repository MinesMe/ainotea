# file: services/ai_processor.py

import requests
from bs4 import BeautifulSoup
from typing import List, Union

# Импортируем только схемы, так как нам не нужны реальные клиенты API
from db.schemas import TextBlock, TranscriptBlock

# --- Сообщения для логов, чтобы было понятно, что сервисы отключены ---
print("AI PROCESSOR: All Google Cloud services are DISABLED (using stubs).")


# --- Функции-заглушки вместо реальных вызовов AI ---

def summarize_and_structure_text(text: str, original_type: str) -> (str, List[TextBlock]):
    """
    ЗАГЛУШКА: Вместо обращения к Gemini, просто возвращает заголовок
    и исходный текст в виде одного блока.
    """
    print("--- Using STUB for summarize_and_structure_text ---")
    if not text or len(text.strip()) < 1:
        return "Пустая заметка", [TextBlock(text="Содержимое отсутствует.")]

    # Создаем простой заголовок
    title = f"Заметка из '{original_type}': {text[:30]}..."
    # Возвращаем исходный текст как есть, в виде одного блока
    structured_content = [TextBlock(header="Основной текст", text=text)]

    return title, structured_content


def extract_text_from_photo(file_path: str) -> str:
    """
    ЗАГЛУШКА: Имитирует распознавание текста с фото.
    Возвращает заранее заданный текст.
    """
    print(f"--- Using STUB for extract_text_from_photo (file: {file_path}) ---")
    return "Это тестовый текст, распознанный с изображения. Функция OCR отключена."


def transcribe_audio(file_path: str) -> (str, List[TranscriptBlock]):
    """
    ЗАГЛУШКА: Имитирует транскрибацию аудио.
    Возвращает заранее заданный текст и структуру транскрипта.
    """
    print(f"--- Using STUB for transcribe_audio (file: {file_path}) ---")
    
    # Имитируем полный текст для суммаризации
    full_text = "Это тестовая транскрибация аудиозаписи. Функция распознавания речи отключена."
    
    # Имитируем структуру транскрипта для отображения
    transcript_blocks = [
        TranscriptBlock(time_start=0.5, text="Это"),
        TranscriptBlock(time_start=1.0, text="тестовая"),
        TranscriptBlock(time_start=1.8, text="транскрибация"),
        TranscriptBlock(time_start=2.5, text="аудиозаписи."),
    ]
    
    return full_text, transcript_blocks


def extract_text_from_link(url: str) -> str:
    """
    Эта функция остается рабочей, так как не зависит от Google Credentials.
    Извлекает основной текстовый контент со страницы по URL.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        for script_or_style in soup(["script", "style"]):
            script_or_style.decompose()

        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        return text
    except requests.RequestException as e:
        print(f"Error fetching URL {url}: {e}")
        return ""