# file: services/ai_processor.py

import requests
from bs4 import BeautifulSoup
from typing import List, Union

# Импортируем только схемы, так как нам не нужны реальные клиенты API
from db.schemas import TextBlock, TranscriptBlock

# --- Сообщения для логов, чтобы было понятно, что сервисы отключены ---
print("AI PROCESSOR: LLM summarization is DISABLED (using stubs).")
# ПРИМЕЧАНИЕ: Google Cloud Vision и Speech могут быть активны, если credentials предоставлены.


# --- Функции-заглушки и рабочие функции ---

def summarize_and_structure_text(text: str, original_type: str) -> (str, List[TextBlock]):
    """
    ЗАГЛУШКА: Вместо обращения к LLM, просто возвращает заголовок
    и исходный текст в виде одного блока. Эта функция больше не вызывает Gemini.
    """
    print("--- Using STUB for summarize_and_structure_text (LLM is OFF) ---")
    if not text or len(text.strip()) < 1:
        return "Пустая заметка", [TextBlock(text="Содержимое отсутствует.")]

    # Создаем простой заголовок
    title = f"Заметка из '{original_type}': {text[:30]}..."
    # Возвращаем исходный текст как есть, в виде одного блока
    structured_content = [TextBlock(header="Извлеченный текст", text=text)]

    return title, structured_content


def extract_text_from_photo(file_path: str) -> str:
    """
    Эта функция остается РАБОЧЕЙ. Она будет работать, если вы предоставите
    GOOGLE_APPLICATION_CREDENTIALS. Если нет, она вызовет ошибку,
    которую обработает эндпоинт.
    """
    from google.cloud import vision
    print(f"--- Calling Google Vision API for OCR (file: {file_path}) ---")
    vision_client = vision.ImageAnnotatorClient()
    with open(file_path, "rb") as image_file:
        content = image_file.read()
    image = vision.Image(content=content)
    response = vision_client.text_detection(image=image)
    if response.error.message:
        raise Exception(f"Vision API error: {response.error.message}")
    return response.full_text_annotation.text if response.full_text_annotation else ""


def transcribe_audio(file_path: str) -> (str, List[TranscriptBlock]):
    """
    Эта функция остается РАБОЧЕЙ. Она будет работать, если вы предоставите
    GOOGLE_APPLICATION_CREDENTIALS.
    """
    from google.cloud import speech
    print(f"--- Calling Google Speech-to-Text API (file: {file_path}) ---")
    speech_client = speech.SpeechClient()
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
    """
    Эта функция остается РАБОЧЕЙ, так как не зависит от Google Credentials.
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