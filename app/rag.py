import os
import re
from pathlib import Path
from typing import List, Dict, Any
import httpx
import chromadb
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

from app.config import settings

class OllamaEmbeddingFunction(EmbeddingFunction[Documents]):
    """Генерация векторных представлений через локальный сервис Ollama."""
    def __init__(self, base_url: str, model_name: str):
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name

    def __call__(self, input: Documents) -> Embeddings:
        if not input:
            return []
        try:
            response = httpx.post(
                f"{self.base_url}/api/embed",
                json={"model": self.model_name, "input": list(input)},
                timeout=60.0
            )
            response.raise_for_status()
            data = response.json()
            return data["embeddings"]
        except Exception as e:
            raise RuntimeError(
                f"Ошибка генерации эмбеддингов в Ollama ({self.base_url}, модель {self.model_name}): {e}"
            )


def split_markdown_into_chunks(text: str, source_name: str) -> List[Dict[str, Any]]:
    """
    Разбивает Markdown-документ на смысловые фрагменты по заголовкам и секциям.
    """
    sections = re.split(r'\n(?=#{1,3}\s)', text)
    chunks = []
    chunk_index = 0

    for section in sections:
        cleaned = section.strip()
        if not cleaned:
            continue
        
        # Извлекаем заголовок секции, если есть
        lines = cleaned.splitlines()
        first_line = lines[0].strip() if lines else ""
        header = first_line.lstrip("#").strip() if first_line.startswith("#") else "Общая информация"

        # Если секция слишком длинная, делим по абзацам
        if len(cleaned) > 800:
            paragraphs = cleaned.split("\n\n")
            buffer = ""
            for p in paragraphs:
                p_clean = p.strip()
                if not p_clean:
                    continue
                if len(buffer) + len(p_clean) < 600:
                    buffer += ("\n\n" + p_clean if buffer else p_clean)
                else:
                    if buffer:
                        chunk_index += 1
                        chunks.append({
                            "id": f"{source_name}_{chunk_index}",
                            "text": buffer,
                            "metadata": {"source": source_name, "header": header}
                        })
                    buffer = p_clean
            if buffer:
                chunk_index += 1
                chunks.append({
                    "id": f"{source_name}_{chunk_index}",
                    "text": buffer,
                    "metadata": {"source": source_name, "header": header}
                })
        else:
            chunk_index += 1
            chunks.append({
                "id": f"{source_name}_{chunk_index}",
                "text": cleaned,
                "metadata": {"source": source_name, "header": header}
            })

    return chunks


class SupportRAG:
    """Управление коллекцией базы знаний в ChromaDB."""
    def __init__(self):
        os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)
        self.client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
        self.embedding_fn = OllamaEmbeddingFunction(
            base_url=settings.OLLAMA_BASE_URL,
            model_name=settings.EMBEDDING_MODEL
        )
        self.collection = self.client.get_or_create_collection(
            name="support_kb",
            embedding_function=self.embedding_fn
        )

    def index_documents(self, force: bool = False) -> int:
        """Индексирует все markdown-файлы из директории docs."""
        if not force and self.collection.count() > 0:
            return self.collection.count()

        docs_dir = Path(settings.DOCS_DIR)
        if not docs_dir.exists():
            return 0

        # Если принудительно, очищаем старые записи
        if force and self.collection.count() > 0:
            all_ids = self.collection.get()["ids"]
            if all_ids:
                self.collection.delete(ids=all_ids)

        all_chunks = []
        for file_path in docs_dir.glob("*.md"):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            chunks = split_markdown_into_chunks(content, file_path.name)
            all_chunks.extend(chunks)

        if all_chunks:
            self.collection.add(
                ids=[c["id"] for c in all_chunks],
                documents=[c["text"] for c in all_chunks],
                metadatas=[c["metadata"] for c in all_chunks]
            )

        return self.collection.count()

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Семантический поиск релевантных фрагментов по запросу."""
        count = self.collection.count()
        if count == 0:
            self.index_documents()

        if self.collection.count() == 0:
            return []

        actual_k = min(top_k, self.collection.count())
        results = self.collection.query(
            query_texts=[query],
            n_results=actual_k
        )

        formatted = []
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0] if "distances" in results else [0.0] * len(docs)

        for doc, meta, dist in zip(docs, metas, distances):
            formatted.append({
                "content": doc,
                "source": meta.get("source", "unknown"),
                "header": meta.get("header", ""),
                "distance": dist
            })

        return formatted

# Синглтон экземпляр RAG
rag_service = SupportRAG()
