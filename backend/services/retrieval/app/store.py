from __future__ import annotations

import threading

from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

from app.config import settings
from app.vector_store import RecipeVectorStore

_lock = threading.Lock()
_store: RecipeVectorStore | None = None


def get_recipe_store() -> RecipeVectorStore:
    global _store
    if _store is not None:
        return _store

    with _lock:
        if _store is not None:
            return _store

        client_kwargs: dict = {"url": settings.qdrant_url}
        if settings.qdrant_api_key:
            client_kwargs["api_key"] = settings.qdrant_api_key

        qdrant_client = QdrantClient(**client_kwargs)
        model = SentenceTransformer(settings.embedding_model)
        _store = RecipeVectorStore(
            qdrant_client=qdrant_client,
            embedding_model=model,
            collection_name=settings.qdrant_collection,
        )
        return _store
