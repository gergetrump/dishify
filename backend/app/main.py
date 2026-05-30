"""Dishify backend API.

Exposes the README pipeline:
        1. user input -> 2. normalize -> 3. hard filter (Postgres)
        -> 4. vector retrieval (Qdrant) -> 5. rule-based scoring -> 6. LLM reasoning

Optional dependencies (Gemini, Postgres, Qdrant) are picked up from env vars
and stages degrade gracefully when they aren't available -- see
``services.pipeline`` for the orchestration.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

load_dotenv()  # picks up .env at process start so exports aren't required

from .api.routes import recipe as recipe_routes
from .clients.gemini import GeminiClient, GeminiError, get_default_client
from .db import count as db_count
from .db import create_all
from .observability import RequestIdMiddleware, configure_logging
from .services.normalization import IngredientNormalizer
from .services.pipeline import run_pipeline
from .vectorstore import VectorStoreError, get_default_vector_store

configure_logging()
logger = logging.getLogger(__name__)


class Profile(BaseModel):
    diet: str | None = Field(default=None, description="e.g. 'vegetarian', 'vegan'")
    allergies: list[str] = Field(default_factory=list)


class RecommendRequest(BaseModel):
    ingredients: list[str] = Field(..., min_length=1)
    profile: Profile = Field(default_factory=Profile)
    top_k: int = Field(default=5, ge=1, le=20)


class StageReportModel(BaseModel):
    name: str
    status: str
    detail: str | None = None
    latency_ms: float | None = None


class RecommendationModel(BaseModel):
    recipe_id: int
    rank: int
    title: str = ""
    link: str | None = None
    source: str | None = None
    ingredients: list[str] = Field(default_factory=list)
    directions: list[str] = Field(default_factory=list)
    available_ingredients: list[str] = Field(default_factory=list)
    missing_ingredients: list[str] = Field(default_factory=list)
    substitutions: list[str] = Field(default_factory=list)
    reason: str = ""
    score: float = 0.0
    ingredient_match: float = 0.0
    vector_similarity: float = 0.0


class RecommendResponse(BaseModel):
    normalized_ingredients: list[str]
    profile: Profile
    candidate_pool_size: int
    retrieved_count: int
    scored_count: int
    recommendations: list[RecommendationModel] = Field(default_factory=list)
    stages: list[StageReportModel]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown hooks. Idempotent and never raises -- failures are
    logged so /health can still serve."""

    try:
        create_all()
    except Exception:  # pragma: no cover -- defensive
        logger.exception("DB schema creation failed; /recommend will surface it")

    app.state.vector_store = None
    try:
        app.state.vector_store = get_default_vector_store()
        logger.info(
            "vector_store ready: %s",
            type(app.state.vector_store).__name__,
        )
    except VectorStoreError as exc:
        logger.warning("vector_store unavailable: %s", exc)

    yield

    # nothing to dispose right now


app = FastAPI(
    title="Dishify API",
    version="0.3.0",
    description="AI-powered recipe recommendations from ingredients you already have.",
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

# Include recipe API routes (vector DB helpers / search)
app.include_router(recipe_routes.router)


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {
        "status": "ok",
        "service": "dishify-api",
        "recipe_count": _db_count_safe(),
        "vector_store": _vector_store_name(app),
    }


def _db_count_safe() -> int | None:
    from .db import SessionLocal

    try:
        with SessionLocal() as s:
            return db_count(s)
    except Exception:
        return None


def _vector_store_name(app: FastAPI) -> str | None:
    store = getattr(app.state, "vector_store", None)
    return type(store).__name__ if store is not None else None


@app.get("/gemini/health", tags=["meta"])
def gemini_health() -> dict:
    """Verify the Gemini connection is configured and reachable."""

    client = get_default_client()
    if not client.is_configured:
        raise HTTPException(
            status_code=503,
            detail="GEMINI_API_KEY is not set on the server",
        )

    try:
        client.generate_text("ping", temperature=0.0)
    except GeminiError as exc:
        raise HTTPException(
            status_code=502, detail=f"Gemini call failed: {exc}"
        ) from exc

    return {"status": "ok", "model": client.model}


@app.post("/normalize", tags=["pipeline"])
def normalize(payload: RecommendRequest) -> dict:
    """Stage 2 only: normalize a list of raw ingredient strings."""

    normalizer = IngredientNormalizer()
    return {"normalized_ingredients": normalizer.normalize(payload.ingredients)}


@app.post("/recommend", response_model=RecommendResponse, tags=["pipeline"])
def recommend(request: Request, payload: RecommendRequest) -> RecommendResponse:
    """Run the full pipeline."""

    report = run_pipeline(
        payload.ingredients,
        payload.profile.model_dump(),
        top_k_explanation=payload.top_k,
        vector_store=getattr(request.app.state, "vector_store", None),
    )

    return RecommendResponse(
        normalized_ingredients=report.normalized_ingredients,
        profile=payload.profile,
        candidate_pool_size=report.candidate_pool_size,
        retrieved_count=report.retrieved_count,
        scored_count=report.scored_count,
        recommendations=[
            RecommendationModel(
                recipe_id=r.recipe_id,
                rank=r.rank,
                title=r.title,
                link=r.link,
                source=r.source,
                ingredients=r.ingredients,
                directions=r.directions,
                available_ingredients=r.available_ingredients,
                missing_ingredients=r.missing_ingredients,
                substitutions=r.substitutions,
                reason=r.reason,
                score=r.score,
                ingredient_match=r.ingredient_match,
                vector_similarity=r.vector_similarity,
            )
            for r in report.recommendations
        ],
        stages=[
            StageReportModel(
                name=s.name,
                status=s.status,
                detail=s.detail,
                latency_ms=s.latency_ms,
            )
            for s in report.stages
        ],
    )


class GeminiPromptRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    json_mode: bool = False
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)


@app.post("/gemini/generate", tags=["gemini"])
def gemini_generate(payload: GeminiPromptRequest) -> dict:
    """Thin passthrough useful for debugging the Gemini connection end-to-end."""

    client: GeminiClient = get_default_client()
    if not client.is_configured:
        raise HTTPException(status_code=503, detail="GEMINI_API_KEY is not set")

    try:
        if payload.json_mode:
            return {
                "model": client.model,
                "data": client.generate_json(
                    payload.prompt, temperature=payload.temperature
                ),
            }
        return {
            "model": client.model,
            "text": client.generate_text(
                payload.prompt, temperature=payload.temperature
            ),
        }
    except GeminiError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
