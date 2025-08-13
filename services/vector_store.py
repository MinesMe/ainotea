# file: services/vector_store.py

import chromadb
from sentence_transformers import SentenceTransformer
from typing import List, Dict
import os

CHROMA_PATH = "./chroma_db"
COLLECTION_NAME = "notes_collection"

class VectorStore:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=CHROMA_PATH)
        self.embedding_model = SentenceTransformer(
            'paraphrase-multilingual-MiniLM-L12-v2',
            device='cpu'
        )
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )
        print("VectorStore initialized with ChromaDB.")

    def _generate_embedding(self, text: str) -> List[float]:
        if not text:
            return []
        return self.embedding_model.encode(text).tolist()

    def upsert_note(self, note_id: int, user_id: int, text_content: str):
        if not text_content:
            self.delete_note(note_id)
            return
        embedding = self._generate_embedding(text_content)
        self.collection.upsert(
            ids=[str(note_id)],
            embeddings=[embedding],
            metadatas=[{"user_id": user_id}],
            documents=[text_content]
        )
        print(f"Upserted note {note_id} to vector store.")

    def search_notes(self, user_id: int, query_text: str, top_n: int = 10) -> List[int]:
        if not query_text:
            return []
        query_embedding = self._generate_embedding(query_text)
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_n,
            where={"user_id": user_id}
        )
        return [int(note_id) for note_id in results['ids'][0]]

    def delete_note(self, note_id: int):
        self.collection.delete(ids=[str(note_id)])
        print(f"Deleted note {note_id} from vector store.")

# Создаем один экземпляр сервиса для использования во всем приложении
vector_store = VectorStore()