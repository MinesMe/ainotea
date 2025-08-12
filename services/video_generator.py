# file: video_generator.py

import os
import subprocess
from google.cloud import texttospeech
import math

# --- НАСТРОЙКА СУБТИТРОВ ---
# Можете изменить это число, чтобы сделать фрагменты субтитров длиннее или короче
WORDS_PER_CHUNK = 8

# Клиент Google Cloud
# Он будет инициализирован с учетными данными из переменной окружения
try:
    tts_client = texttospeech.TextToSpeechClient()
    print("Google Cloud Text-to-Speech client initialized successfully.")
except Exception as e:
    print(f"Could not initialize Google Cloud client: {e}")
    tts_client = None


# Функция для форматирования времени в формат SRT
def format_time_srt(seconds: float) -> str:
    millisec = int((seconds - int(seconds)) * 1000)
    seconds = int(seconds)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millisec:03d}"


def create_video_from_summary(summary_text: str, background_video_path: str, voice_name: str) -> str:
    if not tts_client:
        raise ConnectionError("Google Cloud Text-to-Speech client not initialized.")

    print(f"Generating audio for text: '{summary_text[:50]}...'")

    # 1. Генерация аудио
    synthesis_input = texttospeech.SynthesisInput(text=summary_text)
    voice = texttospeech.VoiceSelectionParams(language_code="ru-RU", name=voice_name)
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)

    response = tts_client.synthesize_speech(
        input=synthesis_input,
        voice=voice,
        audio_config=audio_config
    )

    temp_audio_path = f"temp_narration_{abs(hash(summary_text))}.mp3"
    with open(temp_audio_path, "wb") as out:
        out.write(response.audio_content)
    print(f"TTS audio saved to {temp_audio_path}")

    # 2. Создание файла субтитров по частям
    temp_srt_path = f"temp_subtitles_{abs(hash(summary_text))}.srt"
    audio_duration = 0.0
    try:
        # Получаем длительность аудио с помощью ffprobe
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1',
             temp_audio_path],
            capture_output=True, text=True, check=True
        )
        audio_duration = float(result.stdout.strip())

        words = summary_text.replace('\n', ' ').split()
        chunks = [' '.join(words[i:i + WORDS_PER_CHUNK]) for i in range(0, len(words), WORDS_PER_CHUNK)]

        if not chunks:
            raise ValueError("No text provided for subtitles.")

        time_per_chunk = audio_duration / len(chunks)

        srt_content = ""
        for i, chunk in enumerate(chunks):
            start_time = i * time_per_chunk
            end_time = start_time + time_per_chunk
            if i == len(chunks) - 1:
                end_time = audio_duration

            srt_content += f"{i + 1}\n"
            srt_content += f"{format_time_srt(start_time)} --> {format_time_srt(end_time)}\n"
            srt_content += f"{chunk}\n\n"

        with open(temp_srt_path, "w", encoding='utf-8') as srt_file:
            srt_file.write(srt_content)
        print(f"Generated sequential subtitles file: {temp_srt_path}")

    except Exception as e:
        print(f"Could not generate subtitles: {e}.")
        if os.path.exists(temp_srt_path):
            os.remove(temp_srt_path)
        temp_srt_path = None

    # 3. Сборка финального видео через FFmpeg
    output_dir = "generated_videos"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    output_filename = f"{output_dir}/final_video_{abs(hash(summary_text))}.mp4"

    # Команда для FFmpeg
    ffmpeg_command = [
        'ffmpeg', '-y',
        '-i', background_video_path,
        '-i', temp_audio_path,
        '-map', '0:v:0',
        '-map', '1:a:0',
        '-c:v', 'libx264',
        '-c:a', 'aac',
        '-shortest'
    ]

    if temp_srt_path and os.path.exists(temp_srt_path):
        # Стиль субтитров можно настраивать здесь
        subtitle_filter = f"subtitles={temp_srt_path}:force_style='Fontname=Arial,FontSize=24,PrimaryColour=&HFFFFFF&,OutlineColour=&H000000&,BorderStyle=1,Outline=1,Shadow=0'"
        ffmpeg_command.extend(['-vf', subtitle_filter])

    ffmpeg_command.append(output_filename)

    print("Running FFmpeg to compose video...")
    try:
        subprocess.run(ffmpeg_command, check=True, capture_output=True, text=True)
        print(f"FFmpeg finished successfully. Final video saved to {output_filename}")
    except subprocess.CalledProcessError as e:
        print("ERROR: FFmpeg failed.")
        print("FFmpeg stderr:", e.stderr)
        raise

    # 4. Очистка временных файлов
    os.remove(temp_audio_path)
    if temp_srt_path and os.path.exists(temp_srt_path):
        os.remove(temp_srt_path)

    return output_filename