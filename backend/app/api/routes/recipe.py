from __future__ import annotations

import os
from typing import List

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(tags=["recipes"])


class ParsedIngredientModel(BaseModel):
    name: str = ""
    quantity: float | None = None
    unit: str | None = None
    raw_text: str = ""


class RecipeDataPointModel(BaseModel):
    title: str = ""
    ingredients: List[str] = Field(default_factory=list)
    parsed_ingredients: List[ParsedIngredientModel] = Field(default_factory=list)
    directions: List[str] = Field(default_factory=list)
    link: str | None = None
    source: str | None = None
    ner: List[str] = Field(default_factory=list)


class IndexRequest(BaseModel):
    recipes: List[RecipeDataPointModel]
    batch_size: int = 100


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=50)
    excluded_ingredients: List[str] | None = None


class SearchHitModel(BaseModel):
    id: int
    score: float
    title: str | None = None
    ingredients: List[str] | None = None
    directions: List[str] | None = None
    link: str | None = None
    source: str | None = None
    ner: List[str] | None = None


@router.post("/recipes/search", response_model=List[SearchHitModel])
def search_recipes(request: Request, payload: SearchRequest):
    """Search recipes by semantic similarity using the configured vector backend.

    If a Qdrant server is configured the endpoint will return full payloads
    (title, ingredients, directions, link, source, ner). Otherwise this will
    perform a vector search against the in-memory backend and return ids + scores.
    """
    try:
        from sentence_transformers import SentenceTransformer
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=503, detail=f"Embedding model unavailable: {exc}")

    embedding_model = SentenceTransformer(os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"))
    query_vector = embedding_model.encode(payload.query).tolist()

    # Prefer explicit Qdrant lookup if URL is configured so we can return payloads.
    qdrant_url = os.getenv("QDRANT_URL", "").strip()
    if qdrant_url:
        try:
            from qdrant_client import QdrantClient
            from backend.app.vector_db.recipe_vector_store import RecipeVectorStore
        except Exception as exc:  # pragma: no cover
            raise HTTPException(status_code=503, detail=f"Qdrant client unavailable: {exc}")

        client = QdrantClient(url=qdrant_url, api_key=os.getenv("QDRANT_API_KEY"))
        store = RecipeVectorStore(qdrant_client=client, embedding_model=embedding_model)
        results = store.retrieve_recipes(payload.query, top_k=payload.top_k, excluded_ingredients=payload.excluded_ingredients)
        return [SearchHitModel(**r) for r in results]

    # Fallback to generic vector store attached to the app (InMemoryVectorStore or Qdrant wrapper)
    vector_store = getattr(request.app.state, "vector_store", None)
    if vector_store is None:
        raise HTTPException(status_code=503, detail="No vector store available on server")

    # vector_store.search expects a raw vector and returns SearchHit-like objects
    try:
        hits = vector_store.search(query_vector, top_k=payload.top_k)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Vector search failed: {exc}")

    return [SearchHitModel(id=h.recipe_id, score=h.score) for h in hits]
