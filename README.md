🚀 Начало работы
1. Предварительные требования
  Перед началом убедитесь, что у вас установлены:
  Python (версия 3.10 или выше)
  PostgreSQL (локально или доступ к облачной инстанции)
  FFmpeg (должен быть доступен в системном PATH)
  Аккаунт Google Cloud с включенными API:
  Cloud Vision API
  Cloud Speech-to-Text API
  Cloud Text-to-Speech API


2. Клонирование репозитория
git clone репозитория
после клонирования переходим в папку - cd ai-note-taker-backend


3. Создание виртуального окружения
  python -m venv venv

Активация
  На Windows (PowerShell):
.\venv\Scripts\activate
  На macOS/Linux:
source venv/bin/activate

4. Установка зависимостей
   pip install -r requirements.txt

5.Создай .env файл - пример скинул в тг

    DATABASE_URL: Строка подключения к вашей базе данных PostgreSQL.
    
    Формат: postgresql://USER:PASSWORD@HOST:PORT/DB_NAME
    
    SECRET_KEY: Сгенерируйте надежный секретный ключ для подписи JWT токенов.
    
    GOOGLE_APPLICATION_CREDENTIALS: Путь к вашему JSON-файлу с ключами сервисного аккаунта Google Cloud. Положите этот файл в корень проекта.


6. uvicorn main:app --reload
