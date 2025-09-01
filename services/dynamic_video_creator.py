# file: services/dynamic_video_creator.py

import os
import uuid
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import VideoFileClip, AudioFileClip
from openai import OpenAI
from core.config import settings
import shutil
import httpx
import time
import traceback

# --- Инициализация (как в вашем коде) ---
custom_http_client = httpx.Client()
client = OpenAI(
    api_key=settings.OPENAI_API_KEY,
    http_client=custom_http_client
)
FONT_PATH = "assets/Arimo-Italic-VariableFont_wght.ttf"

# --- Функция создания субтитров (из вашего оригинального кода) ---
def create_subtitle_image(text, frame_width, font_size=70):
    try:
        font = ImageFont.truetype(FONT_PATH, font_size)
    except IOError:
        raise FileNotFoundError(f"Файл шрифта не найден по пути: {FONT_PATH}")

    # Создаем прозрачное изображение
    text_image = Image.new("RGBA", (frame_width, font_size + 40), (255, 255, 255, 0))
    draw = ImageDraw.Draw(text_image)
    
    # Рассчитываем позицию для центрирования
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    x = (frame_width - text_width) / 2
    y = 10
    
    # Рисуем обводку (тень)
    stroke_width = 2
    draw.text((x - stroke_width, y - stroke_width), text, font=font, fill="black")
    draw.text((x + stroke_width, y - stroke_width), text, font=font, fill="black")
    draw.text((x - stroke_width, y + stroke_width), text, font=font, fill="black")
    draw.text((x + stroke_width, y + stroke_width), text, font=font, fill="black")
    
    # Рисуем основной текст
    draw.text((x, y), text, font=font, fill="white")
    return np.array(text_image)


# --- Основная функция с вашей логикой и нашей обработкой ошибок ---
def create_dynamic_subtitle_video(text: str, background_video_path: str) -> str:
    temp_dir = f"temp_output/{uuid.uuid4().hex}"
    os.makedirs(temp_dir, exist_ok=True)

    audio_path = os.path.join(temp_dir, "voice.mp3")
    silent_video_path = os.path.join(temp_dir, "silent_video.mp4")
    final_video_path = f"generated_videos/{uuid.uuid4().hex}.mp4"

    cap = None
    audio_clip = None
    video_clip = None
    final_clip = None

    try:
        # Шаг 1: Генерация аудио
        response = client.audio.speech.create(model="tts-1-hd", voice="nova", input=text)
        response.stream_to_file(audio_path)

        # Шаг 2: Транскрибация
        with open(audio_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1", file=audio_file, response_format="verbose_json", timestamp_granularities=["word"]
            )
        word_level_info = transcription.words
        if not word_level_info:
            raise HTTPException(status_code=500, detail="Не удалось получить временные метки.")

        # Шаг 3: Сборка видео (полностью ваша логика)
        audio_clip = AudioFileClip(audio_path)
        audio_duration = audio_clip.duration
        cap = cv2.VideoCapture(background_video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(silent_video_path, fourcc, fps, (width, height))

        frame_number = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break

            current_time = frame_number / fps
            if current_time > audio_duration: break
            
            current_word = next((word['word'] for word in word_level_info if word['start'] <= current_time < word['end']), "")
            
            if current_word:
                subtitle_rgba = create_subtitle_image(current_word, width)
                
                # Позиционирование субтитра внизу кадра
                y_offset = height - subtitle_rgba.shape[0] - 50 # Немного поднимем от края
                y1, y2 = y_offset, y_offset + subtitle_rgba.shape[0]
                x1, x2 = 0, subtitle_rgba.shape[1]

                # Ваша логика наложения через альфа-канал
                alpha_s = subtitle_rgba[:, :, 3] / 255.0
                alpha_l = 1.0 - alpha_s
                for c in range(0, 3):
                    frame[y1:y2, x1:x2, c] = (alpha_s * subtitle_rgba[:, :, c] + alpha_l * frame[y1:y2, x1:x2, c])

            out.write(frame)
            frame_number += 1
        
        # Освобождаем ресурсы OpenCV
        out.release()
        cap.release()
        cap = None

        # Шаг 4: Соединение видео и аудио
        video_clip = VideoFileClip(silent_video_path)
        final_clip = video_clip.set_audio(audio_clip)
        final_clip.write_videofile(final_video_path, codec="libx264", audio_codec="aac")
        
        return final_video_path

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Произошла ошибка: {str(e)}")

    finally:
        # --- Наша надежная очистка ---
        if audio_clip: audio_clip.close()
        if video_clip: video_clip.close()
        if final_clip: final_clip.close()
        if cap and cap.isOpened(): cap.release()
        if os.path.exists(temp_dir): shutil.rmtree(temp_dir, ignore_errors=True)
        if os.path.exists(background_video_path):
            try:
                os.remove(background_video_path)
            except Exception as e:
                print(f"Не удалось удалить загруженное видео. Ошибка: {e}")