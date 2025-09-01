# file: services/ai_processor.py

import json
import httpx  # Импортируем httpx для создания HTTP-клиентов
from openai import OpenAI, AsyncOpenAI
from core.config import settings

# --- ИНИЦИАЛИЗАЦИЯ КЛИЕНТОВ OPENAI ---

# ПОЧЕМУ МЫ ДЕЛАЕМ ЭТО ВРУЧНУЮ?
# --------------------------------
# Библиотека openai v1.35.0+ имеет внутренний конфликт с библиотекой httpx v0.28.1+.
# Если инициализировать клиент OpenAI стандартным способом (AsyncOpenAI(api_key=...)),
# он пытается создать внутренний httpx-клиент с устаревшим параметром 'proxies', что вызывает ошибку.
#
# РЕШЕНИЕ:
# Мы создаем httpx-клиент самостоятельно и передаем его в OpenAI.
# Таким образом, мы обходим проблемный код внутренней инициализации.

# 1. Асинхронный клиент для всех основных функций (GPT-4o)
async_http_client = httpx.AsyncClient()
async_openai_client = AsyncOpenAI(
    api_key=settings.OPENAI_API_KEY,
    http_client=async_http_client
)

# 2. Синхронный клиент специально для транскрибации Whisper
sync_http_client = httpx.Client()
sync_openai_client = OpenAI(
    api_key=settings.OPENAI_API_KEY,
    http_client=sync_http_client
)


# --- АСИНХРОННЫЕ ФУНКЦИИ ДЛЯ РАБОТЫ С GPT ---

async def translate_text(text: str, language: str) -> dict | str:
    """
    Переводит текст на указанный язык с помощью OpenAI.

    :param text: Текст для перевода.
    :param language: Целевой язык (например, "Russian").
    :return: Словарь с переведенным текстом или строка с ошибкой.
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
        response = await async_openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        print(f"Error during translation with OpenAI: {e}")
        return f"Error during translation: {e}"

async def generate_summary(text: str) -> dict | str:
    """
    Генерирует краткое содержание текста с помощью OpenAI.

    :param text: Текст для суммаризации.
    :return: Словарь с саммари или строка с ошибкой.
    """
    prompt = f"""
    Create a concise summary of the following text. The summary should capture the main points and key information.
    Provide the result as a JSON object with a single key "summary".
    Text to summarize:
    ---
    {text}
    ---
    """
    try:
        response = await async_openai_client.chat.completions.create(
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

async def generate_flashcards(text: str) -> dict | str:
    """
    Генерирует флеш-карты (термин-определение) по тексту с помощью OpenAI.

    :param text: Текст для обработки.
    :return: Словарь с флеш-картами или строка с ошибкой.
    """
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
        response = await async_openai_client.chat.completions.create(
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

async def generate_quiz(text: str) -> dict | str:
    """
    Генерирует квиз с вопросами и вариантами ответов по тексту с помощью OpenAI.

    :param text: Текст для обработки.
    :return: Словарь с квизом или строка с ошибкой.
    """
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
        response = await async_openai_client.chat.completions.create(
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


# --- СИНХРОННАЯ ФУНКЦИЯ ДЛЯ ТРАНСКРИБАЦИИ АУДИО ---

def transcribe_audio_with_whisper(file_path: str) -> str:
    """
    Транскрибирует аудиофайл с помощью OpenAI Whisper, используя синхронный клиент.

    :param file_path: Путь к аудиофайлу.
    :return: Распознанный текст или пустая строка в случае ошибки.
    """
    try:
        with open(file_path, "rb") as audio_file:
            transcript = sync_openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        return transcript.text
    except Exception as e:
        print(f"Error during audio transcription with OpenAI: {e}")
        return ""
async def get_gpt_chat_response(user_text: str) -> dict | str:
    """
    Отправляет текстовое сообщение пользователя в GPT и возвращает ответ.

    :param user_text: Сообщение от пользователя.
    :return: Словарь с ответом от модели или строка с ошибкой.
    """
    try:
        response = await async_openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": user_text}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        reply_text = response.choices[0].message.content
        return {"reply": reply_text}
    except Exception as e:
        print(f"Error during GPT chat completion: {e}")
        return f"Error during GPT chat completion: {e}"