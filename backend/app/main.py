"""Dishify backend API.

Provides a semantic search route plus Keycloak-backed user preferences.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import List

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

load_dotenv()  # picks up .env at process start so exports aren't required

from .auth import get_current_user_id
from .db import create_all, get_session
from .db.repository import (
    allowed_recipe_ids_by_profile,
    get_user_preferences,
    set_user_preferences,
)
from .observability import RequestIdMiddleware, configure_logging
from .vector_db.recipe_vector_store import RecipeVectorStore

configure_logging()


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=50)
    excluded_ingredients: List[str] | None = None
    available_ingredients: List[str] | None = None


class SearchHitModel(BaseModel):
    id: int
    score: float
    title: str | None = None
    ingredients: List[str] | None = None
    directions: List[str] | None = None
    link: str | None = None
    source: str | None = None
    ner: List[str] | None = None


class UserPreferences(BaseModel):
    excluded_ingredients: List[str] = Field(default_factory=list)
    diet: str | None = None
    allergies: List[str] = Field(default_factory=list)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown hooks. Idempotent and never raises."""

    create_all()
    yield


app = FastAPI(
    title="Dishify API",
    version="0.3.0",
    description="AI-powered recipe search from a single NLP query.",
    lifespan=lifespan,
)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/recipes/search", response_model=List[SearchHitModel], tags=["recipes"])
def search_recipes(
    payload: SearchRequest,
    user_id: str = Depends(get_current_user_id),
    session: Session = Depends(get_session),
):
    """Search recipes by semantic similarity using the configured vector backend."""

    try:
        from sentence_transformers import SentenceTransformer
    except Exception as exc:  # pragma: no cover
        raise HTTPException(
            status_code=503, detail=f"Embedding model unavailable: {exc}"
        )

    embedding_model = SentenceTransformer(
        os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    )
    query_vector = embedding_model.encode(payload.query).tolist()

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
    if qdrant_url:
        try:
            from qdrant_client import QdrantClient
        except Exception as exc:  # pragma: no cover
            raise HTTPException(
                status_code=503, detail=f"Qdrant client unavailable: {exc}"
            )

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
            results = [r for r in results if int(r.get("id")) in allowed_set]
        return [SearchHitModel(**r) for r in results]

    raise HTTPException(
        status_code=503,
        detail="QDRANT_URL is not set; no vector search backend is configured",
    )


@app.get("/me/preferences", response_model=UserPreferences, tags=["users"])
def get_preferences(
    user_id: str = Depends(get_current_user_id),
    session: Session = Depends(get_session),
):
    user_prefs = get_user_preferences(session, user_id)
    return UserPreferences(
        excluded_ingredients=user_prefs["excluded_ingredients"],
        diet=user_prefs["diet"],
        allergies=user_prefs["allergies"],
    )


@app.put("/me/preferences", response_model=UserPreferences, tags=["users"])
def set_preferences(
    payload: UserPreferences,
    user_id: str = Depends(get_current_user_id),
    session: Session = Depends(get_session),
):
    values = set_user_preferences(
        session,
        user_id=user_id,
        excluded_ingredients=payload.excluded_ingredients,
        diet=payload.diet,
        allergies=payload.allergies,
    )
    return UserPreferences(
        excluded_ingredients=values["excluded_ingredients"],
        diet=values["diet"],
        allergies=values["allergies"],
    )


# uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
