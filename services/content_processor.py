# file: services/content_processor.py

from youtube_transcript_api import YouTubeTranscriptApi
import docx
import fitz
import os

def get_text_from_youtube(url: str):
    """
    Пытается получить существующие субтитры из видео на YouTube.
    Использует библиотеку youtube-transcript-api.
    Возвращает текст в случае успеха, иначе None.
    """
    video_id = None
    # Улучшаем извлечение ID для разных форматов ссылок
    if "v=" in url:
        video_id = url.split("v=")[-1].split("&")[0]
    elif "youtu.be/" in url:
        video_id = url.split("youtu.be/")[-1].split("?")[0]
    
    if not video_id:
        print(f"Could not extract video_id from URL: {url}")
        return None

    try:
        print(f"Attempting to fetch transcript for video_id: {video_id} using youtube-transcript-api...")
        # Пытаемся получить вручную созданные или автоматически сгенерированные
        # транскрипты на английском или русском языках.
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'ru'])
        
        # Собираем текст из всех полученных фрагментов
        full_transcript = " ".join([item['text'] for item in transcript_list])
        
        print(f"Successfully fetched subtitles for YouTube video: {video_id}")
        return full_transcript
        
    except Exception as e:
        # Эта ошибка возникает, если субтитры не найдены или доступ к ним ограничен
        print(f"Could not get subtitles for video_id {video_id} using youtube-transcript-api. Reason: {e}.")
        return None


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