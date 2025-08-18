# file: services/ai_processor.py

from openai import AsyncOpenAI, OpenAI # <-- ДОБАВЛЯЕМ СИНХРОННЫЙ OpenAI В ИМПОРТ
from core.config import settings
from typing import List, Dict, Any
import os
import json

# --- Инициализация АСИНХРОННОГО клиента OpenAI ---
try:
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    print("Async OpenAI client initialized successfully.")
except Exception as e:
    client = None
    print(f"CRITICAL: Could not initialize OpenAI client. Error: {e}")


# --- Функция для транскрибации аудио (теперь работает правильно) ---
def transcribe_audio_with_whisper(file_path: str) -> str:
    # Для синхронной функции создаем временный синхронный клиент
    try:
        # Используем импортированный синхронный клиент
        sync_client = OpenAI(api_key=settings.OPENAI_API_KEY)
        print(f"--- Transcribing audio file: {file_path} with Whisper ---")
        with open(file_path, "rb") as audio_file:
            transcript = sync_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )
        return transcript
    except Exception as e:
        print(f"Error during Whisper transcription: {e}")
        return f"Ошибка транскрибации аудио: {e}"


# --- Функции для генерации контента с помощью ChatGPT (без изменений) ---

async def generate_summary(text: str) -> Dict[str, Any]:
    prompt = f"""
    Проанализируй следующий текст и создай для него краткое, но емкое саммари.
    Верни результат СТРОГО в виде словаря Python с ключами "key_points" и "conclusion".
    Пример: {{"key_points": ["Тезис 1."], "conclusion": "Вывод."}}
    Текст:
    ---
    {text}
    ---
    """
    response_obj = await _call_chatgpt_and_parse(prompt)
    if not response_obj:
        return {"key_points": ["Ошибка генерации."], "conclusion": "Не удалось разобрать ответ от AI."}
    return response_obj

async def generate_flashcards(text: str) -> List[Dict[str, str]]:
    prompt = f"""
    Проанализируй текст и создай набор флеш-карт.
    Верни результат СТРОГО в виде списка словарей Python.
    Пример: [{{"term": "Термин", "definition": "Определение"}}]
    Текст:
    ---
    {text}
    ---
    """
    response_obj = await _call_chatgpt_and_parse(prompt)
    if not response_obj:
        return [{"term": "Ошибка генерации", "definition": "Не удалось разобрать ответ от AI."}]
    return response_obj

async def generate_quiz(text: str) -> Dict[str, Any]:
    prompt = f"""
    Проанализируй текст и создай квиз.
    Верни результат СТРОГО в виде словаря Python с ключами "title" и "questions".
    Пример: {{"title": "Квиз", "questions": [{{"question": "Вопрос?", "options": [], "correct_answer": "", "explanation": ""}}]}}
    Текст:
    ---
    {text}
    ---
    """
    response_obj = await _call_chatgpt_and_parse(prompt)
    if not response_obj:
        return {"title": "Ошибка генерации", "questions": []}
    return response_obj


async def _call_chatgpt_and_parse(prompt: str) -> Any:
    if not client:
        raise ConnectionError("OpenAI client is not initialized.")
    
    print("--- Calling ChatGPT API (gpt-4o) ---")
    try:
        chat_completion = await client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "Ты — полезный ИИ-ассистент. Всегда отвечай СТРОГО в формате JSON (словарь или список словарей Python), без какого-либо дополнительного текста или объяснений.",
                },
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="gpt-4o",
        )
        raw_response = chat_completion.choices[0].message.content
        print(f"Raw response from AI: {raw_response}")

        start_brace = raw_response.find('{')
        start_bracket = raw_response.find('[')
        if start_brace == -1 and start_bracket == -1: return None
        if start_brace == -1: start_brace = float('inf')
        if start_bracket == -1: start_bracket = float('inf')
        start_index = min(start_brace, start_bracket)
        end_index = raw_response.rfind('}') if raw_response[start_index] == '{' else raw_response.rfind(']')
        if end_index == -1: return None
        json_string = raw_response[start_index : end_index + 1]
        return json.loads(json_string)

    except Exception as e:
        print(f"Error during ChatGPT call or parsing: {e}")
        return None