# file: services/youtube_helper.py

import sys
import time
import random
import requests
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from youtube_transcript_api._api import YouTubeTranscriptApi as YTApi

def _extract_video_id(url: str) -> str | None:
    video_id = None
    if "v=" in url:
        video_id = url.split("v=")[-1].split("&")[0]
    elif "youtu.be/" in url:
        video_id = url.split("youtu.be/")[-1].split("?")[0]
    return video_id

def _setup_anti_detection():
    """Настраивает анти-детекцию для requests."""
    # Ротация User-Agent'ов
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0'
    ]
    
    headers = {
        'User-Agent': random.choice(user_agents),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0'
    }
    
    return headers

def _patch_youtube_api():
    """Патчит YouTube API для обхода блокировок."""
    original_get = requests.Session.get
    
    def patched_get(self, url, **kwargs):
        # Добавляем анти-детекцию заголовки
        headers = _setup_anti_detection()
        if 'headers' in kwargs:
            kwargs['headers'].update(headers)
        else:
            kwargs['headers'] = headers
            
        # Добавляем случайную задержку
        time.sleep(random.uniform(0.5, 2.0))
        
        # Добавляем timeout
        if 'timeout' not in kwargs:
            kwargs['timeout'] = 30
            
        return original_get(self, url, **kwargs)
    
    requests.Session.get = patched_get

def fetch_transcript(url: str) -> str | None:
    video_id = _extract_video_id(url)
    if not video_id:
        print(f"Could not extract video_id from URL: {url}")
        return None

    # Патчим API для анти-детекции
    _patch_youtube_api()
    
    priority_languages = ['ru', 'en', 'auto']
    max_retries = 3
    
    for lang in priority_languages:
        for attempt in range(max_retries):
            try:
                print(f"Попытка {attempt + 1}/{max_retries} для языка '{lang}'...")
                
                # Случайная задержка между попытками
                if attempt > 0:
                    delay = random.uniform(2, 5)
                    print(f"Ждем {delay:.1f} секунд перед повторной попыткой...")
                    time.sleep(delay)
                
                # Получаем транскрипт
                if lang == 'auto':
                    # Пробуем получить любой доступный транскрипт
                    transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                    available_transcripts = list(transcript_list)
                    if available_transcripts:
                        transcript_data = available_transcripts[0].fetch()
                        full_text = " ".join([item['text'] for item in transcript_data])
                        print(f"Успех! Получен автоматический транскрипт.")
                        return full_text
                else:
                    transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=[lang])
                    full_text = " ".join([item['text'] for item in transcript_list])
                    print(f"Успех! Субтитры для языка '{lang}' получены.")
                    return full_text
                    
            except NoTranscriptFound:
                print(f"Субтитры для языка '{lang}' не найдены.")
                break  # Нет смысла повторять для этого языка
            except TranscriptsDisabled:
                print(f"Субтитры отключены для видео {video_id}.")
                return None
            except Exception as e:
                error_msg = str(e).lower()
                if 'too many requests' in error_msg or 'rate limit' in error_msg:
                    print(f"Превышен лимит запросов, ждем дольше...")
                    time.sleep(random.uniform(10, 20))
                elif 'blocked' in error_msg or 'forbidden' in error_msg:
                    print(f"Запрос заблокирован, меняем стратегию...")
                    time.sleep(random.uniform(5, 10))
                else:
                    print(f"Ошибка для '{lang}' (попытка {attempt + 1}): {e}")
                
                if attempt == max_retries - 1:
                    print(f"Все попытки для языка '{lang}' исчерпаны.")
                    break

    print(f"Не удалось получить субтитры для видео {video_id}.")
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