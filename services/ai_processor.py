# file: services/ai_processor.py

# import google.generativeai as genai  <-- ЗАКОММЕНТИРОВАЛИ
from google.cloud import vision, speech
import requests
from bs4 import BeautifulSoup
from typing import List, Union

# Импортируем наши настройки и схемы Pydantic
from core.config import settings
from db.schemas import TextBlock, TranscriptBlock

# --- Инициализация клиентов API ---

# 1. Конфигурируем Gemini API - ЭТА ЧАСТЬ ТЕПЕРЬ НЕ НУЖНА
# try:
#     genai.configure(api_key=settings.GOOGLE_API_KEY)
#     gemini_model = genai.GenerativeModel('gemini-1.5-flash')
#     print("Google Gemini AI client initialized.")
# except Exception as e:
#     print(f"Error initializing Gemini AI client: {e}")
#     gemini_model = None
gemini_model = None # Просто указываем, что его нет
print("Google Gemini AI client is DISABLED.")


# 2. Инициализируем другие клиенты Google Cloud (Vision, Speech)
try:
    vision_client = vision.ImageAnnotatorClient()
    speech_client = speech.SpeechClient()
    print("Google Vision and Speech clients initialized.")
except Exception as e:
    print(f"Error initializing Google Cloud clients: {e}")
    vision_client = None
    speech_client = None


# --- Основные функции сервиса ---

def summarize_and_structure_text(text: str, original_type: str) -> (str, List[TextBlock]):
    """
    ЗАГЛУШКА: Вместо обращения к Gemini, просто возвращает заголовок
    и исходный текст в виде одного блока.
    """
    print("--- Using STUB for summarize_and_structure_text ---")
    if not text or len(text.strip()) < 1:
        return "Пустая заметка", [TextBlock(text="Содержимое отсутствует.")]

    # Создаем простой заголовок
    title = f"Заметка из {original_type}: {text[:30]}..."
    # Возвращаем исходный текст как есть, в виде одного блока
    structured_content = [TextBlock(text=text)]

    return title, structured_content


def extract_text_from_photo(file_path: str) -> str:
    """Распознает текст на изображении с помощью Google Vision AI (OCR)."""
    if not vision_client:
        raise ConnectionError("Vision Client not initialized.")
    with open(file_path, "rb") as image_file:
        content = image_file.read()
    image = vision.Image(content=content)
    response = vision_client.text_detection(image=image)
    if response.error.message:
        raise Exception(f"Vision API error: {response.error.message}")
    return response.full_text_annotation.text if response.full_text_annotation else ""


def transcribe_audio(file_path: str) -> (str, List[TranscriptBlock]):
    """Транскрибирует аудиофайл, возвращая полный текст и структурированный транскрипт."""
    if not speech_client:
        raise ConnectionError("Speech Client not initialized.")

    with open(file_path, "rb") as audio_file:
        content = audio_file.read()

    audio = speech.RecognitionAudio(content=content)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.MP3,
        sample_rate_hertz=16000,
        language_code="ru-RU",
        enable_automatic_punctuation=True,
        enable_word_time_offsets=True,
    )

    operation = speech_client.long_running_recognize(config=config, audio=audio)
    print("Waiting for audio transcription to complete...")
    response = operation.result(timeout=300)

    full_text = []
    transcript_blocks = []
    for result in response.results:
        alternative = result.alternatives[0]
        full_text.append(alternative.transcript)
        for word_info in alternative.words:
            transcript_blocks.append(
                TranscriptBlock(
                    time_start=word_info.start_time.total_seconds(),
                    text=word_info.word
                )
            )

    return " ".join(full_text), transcript_blocks


def extract_text_from_link(url: str) -> str:
    """Извлекает основной текстовый контент со страницы по URL."""
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