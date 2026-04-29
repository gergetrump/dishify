"""Dishify backend API.

Exposes the README pipeline:
	1. user input -> 2. normalize -> 3. hard filter (Postgres)
	-> 4. vector retrieval (Qdrant) -> 5. rule-based scoring -> 6. LLM reasoning

Optional dependencies (Gemini, Postgres, Qdrant) are picked up from env vars
and stages degrade gracefully when they aren't available -- see
``services.pipeline`` for the orchestration.
"""

from __future__ import annotations

from typing import List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

load_dotenv()  # picks up .env at process start so exports aren't required

from .clients.gemini import GeminiClient, GeminiError, get_default_client  # noqa: E402
from .db import count as db_count, create_all  # noqa: E402
from .services.normalization import IngredientNormalizer  # noqa: E402
from .services.pipeline import run_pipeline  # noqa: E402


class Profile(BaseModel):
	diet: Optional[str] = Field(default=None, description="e.g. 'vegetarian', 'vegan'")
	allergies: List[str] = Field(default_factory=list)


class RecommendRequest(BaseModel):
	ingredients: List[str] = Field(..., min_length=1)
	profile: Profile = Field(default_factory=Profile)
	top_k: int = Field(default=5, ge=1, le=20)


class StageReportModel(BaseModel):
	name: str
	status: str
	detail: Optional[str] = None


class RecommendationModel(BaseModel):
	recipe_id: int
	rank: int
	reason: str
	missing_ingredients: List[str] = Field(default_factory=list)
	substitutions: List[str] = Field(default_factory=list)


class RecommendResponse(BaseModel):
	normalized_ingredients: List[str]
	profile: Profile
	candidate_pool_size: int
	retrieved_count: int
	scored_count: int
	recommendations: List[RecommendationModel] = Field(default_factory=list)
	stages: List[StageReportModel]


app = FastAPI(
	title="Dishify API",
	version="0.2.0",
	description="AI-powered recipe recommendations from ingredients you already have.",
)

app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=False,
	allow_methods=["*"],
	allow_headers=["*"],
)


@app.on_event("startup")
def _on_startup() -> None:
	# Idempotent: ensures the recipes table exists when running on a fresh SQLite file.
	try:
		create_all()
	except Exception:
		# Don't crash startup if the DB is unreachable; /recommend will surface it.
		pass


@app.get("/health", tags=["meta"])
def health() -> dict:
	try:
		recipes = db_count_safe()
	except Exception as exc:
		recipes = None
	return {"status": "ok", "service": "dishify-api", "recipe_count": recipes}


def db_count_safe() -> Optional[int]:
	from .db import SessionLocal

	try:
		with SessionLocal() as s:
			return db_count(s)
	except Exception:
		return None


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
		raise HTTPException(status_code=502, detail=f"Gemini call failed: {exc}") from exc

	return {"status": "ok", "model": client.model}


@app.post("/normalize", tags=["pipeline"])
def normalize(payload: RecommendRequest) -> dict:
	"""Stage 2 only: normalize a list of raw ingredient strings."""

	normalizer = IngredientNormalizer()
	return {"normalized_ingredients": normalizer.normalize(payload.ingredients)}


@app.post("/recommend", response_model=RecommendResponse, tags=["pipeline"])
def recommend(payload: RecommendRequest) -> RecommendResponse:
	"""Run the full pipeline."""

	report = run_pipeline(
		payload.ingredients,
		payload.profile.model_dump(),
		top_k_explanation=payload.top_k,
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
				reason=r.reason,
				missing_ingredients=r.missing_ingredients,
				substitutions=r.substitutions,
			)
			for r in report.recommendations
		],
		stages=[StageReportModel(name=s.name, status=s.status, detail=s.detail) for s in report.stages],
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
				"data": client.generate_json(payload.prompt, temperature=payload.temperature),
			}
		return {
			"model": client.model,
			"text": client.generate_text(payload.prompt, temperature=payload.temperature),
		}
	except GeminiError as exc:
		raise HTTPException(status_code=502, detail=str(exc)) from exc
