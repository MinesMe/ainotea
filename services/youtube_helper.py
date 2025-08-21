# file: services/youtube_helper.py (ФИНАЛЬНАЯ ВЕРСИЯ С ПРАВИЛЬНЫМ ВЫЗОВОМ)

import sys
# ПРАВИЛЬНЫЙ ИМПОРТ: импортируем сам КЛАСС, а не отдельную функцию
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

def _extract_video_id(url: str) -> str | None:
    video_id = None
    if "v=" in url:
        video_id = url.split("v=")[-1].split("&")[0]
    elif "youtu.be/" in url:
        video_id = url.split("youtu.be/")[-1].split("?")[0]
    return video_id

def fetch_transcript(url: str) -> str | None:
    video_id = _extract_video_id(url)
    if not video_id:
        print(f"Could not extract video_id from URL: {url}")
        return None

    priority_languages = ['ru', 'en']
    
    for lang in priority_languages:
        try:
            print(f"Пытаюсь получить субтитры для языка: '{lang}'...")
            
            # ПРАВИЛЬНЫЙ ВЫЗОВ: вызываем метод .get_transcript() на классе YouTubeTranscriptApi
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=[lang])
            
            full_text = " ".join([item['text'] for item in transcript_list])
            
            print(f"Успех! Субтитры для языка '{lang}' получены.")
            return full_text
        except NoTranscriptFound:
            print(f"Субтитры для языка '{lang}' не найдены.")
            continue
        except TranscriptsDisabled:
            print(f"Субтитры отключены для видео {video_id}.")
            return None
        except Exception as e:
            print(f"Произошла непредвиденная ошибка при получении субтитров для '{lang}': {e}.")
            continue

    print(f"Не удалось найти субтитры ни на одном из приоритетных языков для видео {video_id}.")
    return None

# Тестовый блок
if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("\nОшибка: Пожалуйста, укажите URL видео в качестве аргумента.")
        sys.exit(1)
    video_url = sys.argv[1]
    print(f"\n--- Начинаю тест модуля youtube_helper.py ---")
    transcript_text = fetch_transcript(video_url)
    print("\n--- РЕЗУЛЬТАТ ТЕСТА ---")
    if transcript_text:
        print(transcript_text)
    else:
        print("Не удалось получить транскрипцию.")