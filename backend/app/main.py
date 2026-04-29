"""Dishify backend API.

The pipeline (see README) goes:
	1. user input  -> 2. normalize  -> 3. hard filter (Postgres)
	-> 4. vector retrieval (Qdrant)  -> 5. rule-based scoring  -> 6. LLM reasoning

Stages 3-6 are not implemented yet; the API exposes the wired-up stages and
returns explicit ``pending`` placeholders for the rest so the contract is
visible to clients and frontend work can start in parallel.
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .clients.gemini import GeminiClient, GeminiError, get_default_client
from .services.normalization import IngredientNormalizer


class Profile(BaseModel):
	diet: Optional[str] = Field(default=None, description="e.g. 'vegetarian', 'vegan'")
	allergies: List[str] = Field(default_factory=list)


class RecommendRequest(BaseModel):
	ingredients: List[str] = Field(..., min_length=1)
	profile: Profile = Field(default_factory=Profile)
	top_k: int = Field(default=5, ge=1, le=20)


class PipelineStage(BaseModel):
	name: str
	status: str
	detail: Optional[str] = None


class RecommendResponse(BaseModel):
	normalized_ingredients: List[str]
	profile: Profile
	recommendations: List[dict] = Field(default_factory=list)
	stages: List[PipelineStage]


app = FastAPI(
	title="Dishify API",
	version="0.1.0",
	description="AI-powered recipe recommendations from ingredients you already have.",
)

app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=False,
	allow_methods=["*"],
	allow_headers=["*"],
)


@app.get("/health", tags=["meta"])
def health() -> dict:
	return {"status": "ok", "service": "dishify-api"}


@app.get("/gemini/health", tags=["meta"])
def gemini_health() -> dict:
	"""Verify the Gemini connection is configured and reachable."""

	client = get_default_client()
	if not client.is_configured:
		raise HTTPException(
			status_code=503,
			detail="GEMINI_API_KEY is not set on the server",
		)
	if not client.ping():
		raise HTTPException(status_code=502, detail="Gemini API unreachable")
	return {"status": "ok", "model": client.model}


@app.post("/normalize", tags=["pipeline"])
def normalize(payload: RecommendRequest) -> dict:
	"""Stage 2 only: normalize a list of raw ingredient strings."""

	normalizer = IngredientNormalizer()
	return {"normalized_ingredients": normalizer.normalize(payload.ingredients)}


@app.post("/recommend", response_model=RecommendResponse, tags=["pipeline"])
def recommend(payload: RecommendRequest) -> RecommendResponse:
	"""Run the full pipeline. Stages 3-6 are stubbed pending implementation."""

	normalizer = IngredientNormalizer()
	normalized = normalizer.normalize(payload.ingredients)

	stages: List[PipelineStage] = [
		PipelineStage(name="normalize", status="ok"),
		PipelineStage(
			name="hard_filter",
			status="pending",
			detail="Postgres hard-constraint filtering not implemented yet.",
		),
		PipelineStage(
			name="vector_retrieval",
			status="pending",
			detail="Qdrant retrieval not implemented yet.",
		),
		PipelineStage(
			name="rule_based_scoring",
			status="pending",
			detail="Scoring not implemented yet.",
		),
		PipelineStage(
			name="llm_reasoning",
			status="pending",
			detail="Final LLM reasoning not implemented yet.",
		),
	]

	return RecommendResponse(
		normalized_ingredients=normalized,
		profile=payload.profile,
		recommendations=[],
		stages=stages,
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
			return {"model": client.model, "data": client.generate_json(payload.prompt, temperature=payload.temperature)}
		return {"model": client.model, "text": client.generate_text(payload.prompt, temperature=payload.temperature)}
	except GeminiError as exc:
		raise HTTPException(status_code=502, detail=str(exc)) from exc
