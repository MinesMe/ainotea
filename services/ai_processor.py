# file: services/ai_processor.py

from openai import AsyncOpenAI
import json
from core.config import settings

# --- Инициализация клиента OpenAI ---
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


# --- НОВАЯ ФУНКЦИЯ ПЕРЕВОДА ---
async def translate_text(text: str, language: str) -> dict:
    """
    Переводит текст на указанный язык с помощью OpenAI,
    возвращая результат в виде JSON.
    """
    prompt = f"""
    Translate the following text into {language}.
    Provide the result as a JSON object with a single key "translated_text".

    Text to translate:
    ---
    {text}
    ---
    """
    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        print(f"Error during translation with OpenAI: {e}")
        # Возвращаем строку с ошибкой, чтобы эндпоинт мог ее обработать
        return f"Error during translation: {e}"


# --- СУЩЕСТВУЮЩИЕ ФУНКЦИИ ---

async def generate_summary(text: str):
    """Генерирует краткое содержание текста."""
    prompt = f"""
    Create a concise summary of the following text.
    The summary should capture the main points and key information.
    Provide the result as a JSON object with a single key "summary".

    Text to summarize:
    ---
    {text}
    ---
    """
    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.5,
        )
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        print(f"Error during summary generation with OpenAI: {e}")
        return f"Error during summary generation: {e}"

async def generate_flashcards(text: str):
    """Генерирует флеш-карты (термин-определение) по тексту."""
    prompt = f"""
    Based on the following text, generate a list of flashcards.
    Each flashcard should be a JSON object with two keys: "term" and "definition".
    Return a single JSON object with one key "flashcards", which contains the list of these objects.

    Text to process:
    ---
    {text}
    ---
    """
    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.5,
        )
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        print(f"Error during flashcards generation with OpenAI: {e}")
        return f"Error during flashcards generation: {e}"

async def generate_quiz(text: str):
    """Гeneрирует квиз с вопросами и вариантами ответов по тексту."""
    prompt = f"""
    Based on the following text, create a quiz with multiple-choice questions.
    Return a single JSON object with a key "quiz", which contains a list of question objects.
    Each question object should have:
    - a "question" (string)
    - "options" (a list of 4 strings)
    - an "answer" (the correct string from the options).

    Text to process:
    ---
    {text}
    ---
    """
    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.7,
        )
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        print(f"Error during quiz generation with OpenAI: {e}")
        return f"Error during quiz generation: {e}"


def transcribe_audio_with_whisper(file_path: str) -> str:
    """Транскрибирует аудиофайл с помощью OpenAI Whisper."""
    # Для Whisper используется синхронный клиент
    from openai import OpenAI
    sync_client = OpenAI(api_key=settings.OPENAI_API_KEY)
    
    try:
        with open(file_path, "rb") as audio_file:
            transcript = sync_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        return transcript.text
    except Exception as e:
        print(f"Error during audio transcription with OpenAI: {e}")
        return ""