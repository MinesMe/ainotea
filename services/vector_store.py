# file: services/vector_store.py

import chromadb
from sentence_transformers import SentenceTransformer
from typing import List, Dict
import os

# Указываем, где будет храниться локальная база данных ChromaDB
CHROMA_PATH = "./chroma_db"
# Имя нашей коллекции векторов
COLLECTION_NAME = "notes_collection"

class VectorStore:
    """
    Класс для управления векторным хранилищем заметок.
    Отвечает за создание, обновление и семантический поиск векторов.
    """
    def __init__(self):
        # Инициализируем клиент ChromaDB.
        # PersistentClient означает, что база будет сохраняться на диск в папку CHROMA_PATH.
        self.client = chromadb.PersistentClient(path=CHROMA_PATH)

        # Загружаем модель для создания эмбеддингов (векторов).
        # 'paraphrase-multilingual-MiniLM-L12-v2' - это хорошая, быстрая и многоязычная модель.
        self.embedding_model = SentenceTransformer(
            'paraphrase-multilingual-MiniLM-L12-v2',
            device='cpu'  # Используем CPU, так как на Railway может не быть GPU
        )

        # Получаем или создаем коллекцию в ChromaDB.
        # Коллекция - это аналог таблицы в реляционной БД.
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            # Указываем, какую модель мы используем для эмбеддингов.
            # Это нужно для совместимости данных.
            metadata={"hnsw:space": "cosine"} # Используем косинусное расстояние для поиска
        )
        print("VectorStore initialized with ChromaDB.")

    def _generate_embedding(self, text: str) -> List[float]:
        """Приватный метод для генерации векторного представления (эмбеддинга) для текста."""
        if not text:
            return []
        # .encode() превращает текст в вектор, .tolist() - в обычный список Python
        embedding = self.embedding_model.encode(text).tolist()
        return embedding

    def upsert_note(self, note_id: int, user_id: int, text_content: str):
        """
        Добавляет или обновляет вектор заметки в хранилище.
        'Upsert' = Update (обновить) + Insert (вставить).

        :param note_id: Уникальный ID заметки из нашей основной БД.
        :param user_id: ID владельца заметки для фильтрации.
        :param text_content: Текстовое содержимое заметки для векторизации.
        """
        if not text_content:
            # Если в заметке нет текста, удаляем ее из векторного хранилища
            self.delete_note(note_id)
            return

        embedding = self._generate_embedding(text_content)

        # upsert - основная команда ChromaDB.
        self.collection.upsert(
            ids=[str(note_id)],  # ID должны быть строками
            embeddings=[embedding],
            # В метаданные мы сохраняем ID пользователя.
            # Это КЛЮЧЕВОЙ момент для безопасности и приватности данных.
            metadatas=[{"user_id": user_id}],
            documents=[text_content] # Сохраняем и сам текст для отладки
        )
        print(f"Upserted note {note_id} to vector store.")

    def search_notes(self, user_id: int, query_text: str, top_n: int = 10) -> List[int]:
        """
        Выполняет семантический поиск похожих заметок для конкретного пользователя.

        :param user_id: ID пользователя, который выполняет поиск.
        :param query_text: Текст поискового запроса.
        :param top_n: Максимальное количество результатов для возврата.
        :return: Список ID найденных заметок, отсортированных по релевантности.
        """
        if not query_text:
            return []

        query_embedding = self._generate_embedding(query_text)

        # Выполняем запрос к коллекции
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_n,
            # Это самая важная часть: мы ищем только среди заметок,
            # где metadata['user_id'] совпадает с ID текущего пользователя.
            where={"user_id": user_id}
        )

        # Извлекаем ID из результатов и преобразуем их в числа
        note_ids = [int(note_id) for note_id in results['ids'][0]]
        return note_ids

    def delete_note(self, note_id: int):
        """Удаляет вектор заметки из хранилища по ее ID."""
        self.collection.delete(ids=[str(note_id)])
        print(f"Deleted note {note_id} from vector store.")

# Создаем один экземпляр сервиса для использования во всем приложении
vector_store = VectorStore()