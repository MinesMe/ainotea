import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from core.config import settings
import sys

# --- Инициализация OpenAI клиента прямо в этом файле ---
try:
    # Мы используем синхронный клиент, так как наша функция синхронная
    sync_client = OpenAI(api_key=settings.OPENAI_API_KEY)
    print("OpenAI client initialized successfully for url_reader_helper.")
except Exception as e:
    sync_client = None
    print(f"CRITICAL: Could not initialize OpenAI client for url_reader_helper. Error: {e}")


def _extract_main_content_with_gpt(text: str) -> str:
    """
    Внутренняя функция, которая использует GPT с продвинутым промптом
    для извлечения основного контента.
    """
    if not sync_client:
        print("OpenAI client is not initialized. Returning original text.")
        return text

    # --- НАШ ПРОДВИНУТЫЙ ПРОМПТ ---
    prompt = f"""
# МИССИЯ
Ты — элитный AI-парсер, специализирующийся на очистке и извлечении веб-контента. Твоя единственная задача — проанализировать предоставленный "сырой" текст, полученный со страницы сайта, и извлечь из него ТОЛЬКО ядро основного контента (статью, пост, описание).

# ПРАВИЛА ИЗВЛЕЧЕНИЯ

## 1. ЧТО НУЖНО БЕЗЖАЛОСТНО УДАЛИТЬ (ЭТО "МУСОР"):
- **Навигация:** Любые меню, хлебные крошки, ссылки "Перейти к содержанию", "Главная страница".
- **Шапка и подвал (Header/Footer):** Всё, что относится к верхней и нижней части сайта (логотипы, контактная информация, ссылки на соцсети).
- **Боковые панели (Sidebars):** Любые колонки с дополнительной информацией, виджетами, календарями.
- **Реклама и призывы к действию:** Все рекламные слоганы, баннеры, кнопки "Подписаться", "Купить сейчас", "Зарегистрироваться".
- **Мета-информация:** Имена авторов, даты публикации (если они не являются частью заголовка), количество просмотров, комментариев.
- **Секции взаимодействия:** Разделы комментариев, формы для отправки сообщений, кнопки "Поделиться".
- **Связанный контент:** Списки "Читайте также", "Похожие статьи", "Популярные посты".
- **Юридическая информация:** Уведомления о cookie, политика конфиденциальности, условия использования, "Все права защищены".

## 2. ЧТО НУЖНО СОХРАНИТЬ (ЭТО "СОКРОВИЩЕ"):
- **Основной заголовок статьи/страницы.**
- **Все подзаголовки** внутри основного контента.
- **Все параграфы, списки и цитаты**, составляющие тело статьи или описания.
- **Текст, который является неотъемлемой частью повествования.**

# АНАЛОГИЯ ДЛЯ ПОНИМАНИЯ
Представь, что ты вырезаешь статью из бумажной газеты. Ты аккуратно вырежешь заголовок и текст самой статьи. Ты НЕ будешь вырезать название газеты, номер страницы, рекламу на соседней колонке или прогноз погоды в углу. Действуй так же.

# ФОРМАТ ВЫВОДА
- Верни ТОЛЬКО очищенный текст.
- НЕ добавляй никаких объяснений, комментариев или фраз вроде "Вот очищенный текст:".
- НЕ делай саммари. Просто извлеки и верни.
- Сохраняй оригинальные абзацы основного контента.

# СЫРОЙ ТЕКСТ ДЛЯ ОБРАБОТКИ:
---
{text}
---
"""
    
    print("--- Вызываю GPT с продвинутым промптом для извлечения контента ---")
    try:
        chat_completion = sync_client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Ты — высокоточный движок для извлечения и очистки веб-контента. Твоя задача — следовать инструкциям пользователя с максимальной педантичностью."},
                {"role": "user", "content": prompt}
            ],
            model="gpt-4o",
            temperature=0.0
        )
        clean_text = chat_completion.choices[0].message.content
        print("--- GPT успешно очистил текст ---")
        return clean_text
    except Exception as e:
        print(f"Ошибка при вызове GPT для очистки текста: {e}. Возвращаю исходный текст.")
        return text


def get_text_from_url(url: str) -> str | None:
    """
    Основная функция, которую вызывает api/notes.py.
    Загружает веб-страницу, извлекает весь текст, а затем
    использует GPT для очистки и получения только основного контента.
    """
    print(f"--- Шаг 1: Получаю 'сырые' данные со страницы: {url} ---")
    
    try:
        # --- Часть 1: Скрейпинг с помощью BeautifulSoup ---
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        for script_or_style in soup(['script', 'style']):
            script_or_style.extract()
        
        raw_text = soup.get_text()
        lines = (line.strip() for line in raw_text.splitlines())
        clean_raw_text = '\n'.join(line for line in lines if line)
        
        if not clean_raw_text:
            print("--- BeautifulSoup не смог извлечь текст. ---")
            return None
        
        print("--- 'Сырой' текст успешно извлечен. ---")
        
        # --- Часть 2: Отправляем "сырой" текст в GPT для очистки ---
        print("--- Шаг 2: Отправляю текст в GPT для извлечения основного контента. ---")
        main_content = _extract_main_content_with_gpt(clean_raw_text)
        
        return main_content

    except requests.exceptions.RequestException as e:
        print(f"Ошибка: Не удалось загрузить страницу. Причина: {e}")
        return None
    except Exception as e:
        print(f"Произошла непредвиденная ошибка: {e}")
        return None
# --- Тестовый блок для запуска с флагом -m ---
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\nОшибка: Пожалуйста, укажите URL в качестве аргумента.")
        print("Пример: python -m services.url_reader_helper \"https://...\"")
        sys.exit(1)
    
    target_url = sys.argv[1]
    print(f"\n--- Начинаю тест модуля services.url_reader_helper ---")
    final_text = get_text_from_url(target_url)
    print("\n--- ИТОГОВЫЙ ТЕКСТ ---")
    if final_text:
        print(final_text)
    else:
        print("Не удалось получить текст.")