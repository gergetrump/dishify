from __future__ import annotations

import os

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.app.db.repository import (
    allowed_recipe_ids_by_profile,
    get_user_preferences,
)
from backend.app.models.api import SearchHitModel, SearchRequest
from backend.app.services.ranking import score_recipes_by_inventory
from backend.app.vector_db.recipe_vector_store import RecipeVectorStore


def run_search(
    payload: SearchRequest, user_id: str, session: Session
) -> list[SearchHitModel]:
    """Run semantic search with hard filters and inventory-aware re-ranking."""

    try:
        from sentence_transformers import SentenceTransformer
    except Exception as exc:  # pragma: no cover
        raise HTTPException(
            status_code=503, detail=f"Embedding model unavailable: {exc}"
        )

    embedding_model = SentenceTransformer(
        os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    )

    user_prefs = get_user_preferences(session, user_id)
    request_exclusions = payload.excluded_ingredients or []
    merged_exclusions = [
        item
        for item in [*user_prefs["excluded_ingredients"], *request_exclusions]
        if isinstance(item, str) and item.strip()
    ]

    allowed_ids = allowed_recipe_ids_by_profile(
        session,
        diet=user_prefs["diet"],
        allergies=user_prefs["allergies"],
        excluded_ingredients=merged_exclusions,
    )
    if allowed_ids == []:
        return []

    qdrant_url = os.getenv("QDRANT_URL", "").strip()
    if not qdrant_url:
        raise HTTPException(
            status_code=503,
            detail="QDRANT_URL is not set; no vector search backend is configured",
        )

    try:
        from qdrant_client import QdrantClient
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=503, detail=f"Qdrant client unavailable: {exc}")

    client = QdrantClient(url=qdrant_url, api_key=os.getenv("QDRANT_API_KEY"))
    store = RecipeVectorStore(
        qdrant_client=client,
        embedding_model=embedding_model,
        collection_name="recipes_10000",
    )
    results = store.retrieve_recipes(
        payload.query,
        top_k=payload.top_k,
        excluded_ingredients=merged_exclusions or None,
        available_ingredients=payload.available_ingredients or None,
    )
    if allowed_ids is not None:
        allowed_set = {int(item) for item in allowed_ids}
        results = [r for r in results if int(r.id) in allowed_set]

    results = score_recipes_by_inventory(
        results,
        payload.available_ingredients or None,
    )
    return [SearchHitModel(**r.model_dump()) for r in results]
