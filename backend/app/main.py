"""Dishify backend API.

Provides a semantic search route plus Keycloak-backed user preferences.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import List

from dotenv import load_dotenv
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

load_dotenv()  # picks up .env at process start so exports aren't required

from .auth import get_current_user_id
from .db import create_all, get_session
from .db.repository import get_user_preferences, set_user_preferences
from .models.api import SearchHitModel, SearchRequest, UserPreferences
from .observability import RequestIdMiddleware, configure_logging
from .services.search import run_search

configure_logging()


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

    return run_search(payload, user_id, session)


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
