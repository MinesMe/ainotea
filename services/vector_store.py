# file: services/vector_store.py

import chromadb
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any

CHROMA_PATH = "./chroma_db"
COLLECTION_NAME = "notes_collection"

class VectorStore:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=CHROMA_PATH)
        # Используем стандартную многоязычную модель для создания векторов (эмбеддингов)
        self.embedding_model = SentenceTransformer(
            'paraphrase-multilingual-MiniLM-L12-v2',
            device='cpu'
        )
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            # Косинусное расстояние отлично подходит для измерения семантической схожести текстов
            metadata={"hnsw:space": "cosine"} 
        )
        print("VectorStore initialized with ChromaDB.")

    def _generate_embedding(self, text: str) -> List[float]:
        """Преобразует текстовый фрагмент в числовой вектор."""
        if not text:
            return []
        return self.embedding_model.encode(text).tolist()

    def _chunk_text(self, text: str) -> List[str]:
        """
        Разбивает большой текст на осмысленные куски (чанки) по параграфам.
        Это ключевой шаг для качественного поиска.
        """
        # Разделяем текст по двойному переносу строки, что обычно соответствует параграфам
        paragraphs = text.split('\n\n')
        chunks = []
        for p in paragraphs:
            # Игнорируем слишком короткие или пустые параграфы
            if len(p.strip()) > 50: 
                chunks.append(p.strip())
        return chunks

    def upsert_note_chunks(self, note_id: int, user_id: int, text_content: str):
        """
        Главная функция для добавления/обновления заметки в векторной базе.
        Разбивает текст на чанки и сохраняет каждый как отдельный вектор.
        """
        # 1. Сначала удаляем все старые чанки для этой заметки, чтобы избежать дублей
        self.delete_note(note_id)

        if not text_content:
            print(f"Note {note_id} has no content to upsert.")
            return

        # 2. Разбиваем новый текст на чанки
        chunks = self._chunk_text(text_content)
        if not chunks:
            print(f"No suitable chunks found for note {note_id}.")
            return

        # 3. Готовим данные для сохранения в ChromaDB
        chunk_ids = [f"{note_id}_{i}" for i in range(len(chunks))]
        embeddings = [self._generate_embedding(chunk) for chunk in chunks]
        metadatas = [{"note_id": note_id, "user_id": user_id} for _ in chunks]

        # 4. Сохраняем все чанки в векторную базу
        self.collection.upsert(
            ids=chunk_ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=chunks
        )
        print(f"Upserted {len(chunks)} chunks for note {note_id} to vector store.")

    def search_notes(self, user_id: int, query_text: str, top_n: int = 5, threshold: float = 0.5) -> List[Dict[str, Any]]:
        """
        Улучшенная и надежная функция поиска. Находит релевантные чанки.
        """
        if not query_text:
            return []
            
        query_embedding = self._generate_embedding(query_text)
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_n,
            where={"user_id": user_id},
            include=["metadatas", "documents", "distances"]
        )
        
        final_results = []
        if results['ids'][0]:
            for i, distance in enumerate(results['distances'][0]):
                # Отсеиваем результаты, которые слишком далеки от запроса (нерелевантны)
                if distance < threshold:
                    metadata = results['metadatas'][0][i]
                    
                    # --- ИСПРАВЛЕНИЕ ЗДЕСЬ: Безопасное получение note_id ---
                    # Используем .get(), чтобы избежать ошибки KeyError, если ключ отсутствует в старых данных
                    note_id = metadata.get('note_id')
                    
                    # Если в метаданных по какой-то причине нет note_id, просто пропускаем этот результат
                    if not note_id:
                        continue
                        
                    matched_text = results['documents'][0][i]
                    final_results.append({
                        "note_id": note_id,
                        "matched_text": matched_text,
                        "relevance": 1 - distance # Преобразуем расстояние в "схожесть" (1.0 = идеально)
                    })

        # Убираем дубликаты, если несколько чанков одной заметки попали в топ.
        # Оставляем только самый релевантный результат для каждой заметки.
        unique_notes = {}
        for res in final_results:
            note_id = res['note_id']
            if note_id not in unique_notes or res['relevance'] > unique_notes[note_id]['relevance']:
                unique_notes[note_id] = res
        
        # Возвращаем отсортированный список уникальных результатов
        return sorted(list(unique_notes.values()), key=lambda x: x['relevance'], reverse=True)

    def delete_note(self, note_id: int):
        """
        Удаляет ВСЕ чанки, связанные с указанной заметкой.
        """
        self.collection.delete(where={"note_id": note_id})
        print(f"Deleted all chunks for note {note_id} from vector store.")

# Создаем один глобальный экземпляр сервиса для использования во всем приложении
vector_store = VectorStore()