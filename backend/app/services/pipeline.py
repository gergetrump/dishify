"""End-to-end orchestration of the README pipeline.

	1. normalize  -> 2. hard filter (Postgres)  -> 3. vector retrieval (Qdrant)
	-> 4. rule-based scoring  -> 5. LLM reasoning

Each stage records its outcome in ``PipelineReport.stages`` so the API can
return clear status to the caller and so we can degrade gracefully when
optional dependencies (Gemini, vector store, DB) are missing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence

from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session

from ..clients.gemini import GeminiClient
from ..db import SessionLocal, Recipe, get_by_ids, hard_filter
from .explanation import Recommendation, explain
from .normalization import IngredientNormalizer
from .ranking import RankedCandidate, fallback_rank_without_vectors, score_candidates, take_top
from .retrieval import RetrievalUnavailable, retrieve_candidates


@dataclass
class StageReport:
	name: str
	status: str  # "ok" | "skipped" | "error" | "pending"
	detail: Optional[str] = None


@dataclass
class PipelineReport:
	normalized_ingredients: List[str]
	stages: List[StageReport] = field(default_factory=list)
	candidate_pool_size: int = 0
	retrieved_count: int = 0
	scored_count: int = 0
	recommendations: List[Recommendation] = field(default_factory=list)


def _record(stages: List[StageReport], name: str, status: str, detail: Optional[str] = None) -> None:
	stages.append(StageReport(name=name, status=status, detail=detail))


def run_pipeline(
	ingredients: Sequence[str],
	profile: dict,
	*,
	top_k_retrieval: int = 50,
	top_k_explanation: int = 5,
	session: Optional[Session] = None,
	gemini_client: Optional[GeminiClient] = None,
) -> PipelineReport:
	stages: List[StageReport] = []
	client = gemini_client or GeminiClient()

	# --- Stage 2: normalization ---
	normalizer = IngredientNormalizer(client=client)
	normalized = normalizer.normalize(ingredients)
	_record(stages, "normalize", "ok", f"{len(normalized)} ingredients")
	report = PipelineReport(normalized_ingredients=normalized, stages=stages)

	if not normalized:
		_record(stages, "hard_filter", "skipped", "No ingredients to query.")
		return report

	# --- Stages 3-5: need DB. ---
	owns_session = session is None
	try:
		db_session = session if session is not None else SessionLocal()
	except SQLAlchemyError as exc:
		_record(stages, "hard_filter", "error", f"DB unavailable: {exc}")
		return report

	try:
		try:
			pool: List[Recipe] = hard_filter(
				db_session,
				diet=profile.get("diet"),
				allergies=profile.get("allergies", []) or [],
			)
		except OperationalError as exc:
			_record(stages, "hard_filter", "error", f"DB query failed: {exc.orig}")
			return report
		report.candidate_pool_size = len(pool)
		_record(stages, "hard_filter", "ok", f"{len(pool)} recipes survived hard constraints")

		if not pool:
			_record(stages, "vector_retrieval", "skipped", "Empty candidate pool")
			_record(stages, "rule_based_scoring", "skipped", "Empty candidate pool")
			_record(stages, "llm_reasoning", "skipped", "Empty candidate pool")
			return report

		# --- Stage 4: vector retrieval ---
		ranked: List[RankedCandidate]
		try:
			candidates = retrieve_candidates(
				normalized,
				allowed_ids=[r.id for r in pool],
				top_k=top_k_retrieval,
				gemini_client=client,
			)
			report.retrieved_count = len(candidates)
			_record(stages, "vector_retrieval", "ok", f"{len(candidates)} hits")

			if not candidates:
				ranked = fallback_rank_without_vectors(pool, normalized, limit=top_k_retrieval)
			else:
				retrieved_recipes = get_by_ids(db_session, [c.recipe_id for c in candidates])
				ranked = score_candidates(candidates, retrieved_recipes, normalized)
		except RetrievalUnavailable as exc:
			_record(stages, "vector_retrieval", "skipped", str(exc))
			ranked = fallback_rank_without_vectors(pool, normalized, limit=top_k_retrieval)

		# --- Stage 5: scoring ---
		report.scored_count = len(ranked)
		_record(stages, "rule_based_scoring", "ok", f"{len(ranked)} scored")

		# --- Stage 6: LLM reasoning ---
		top = take_top(ranked, top_k_explanation)
		recs = explain(normalized, profile, top, gemini_client=client)
		if client.is_configured:
			_record(stages, "llm_reasoning", "ok", f"{len(recs)} recommendations")
		else:
			_record(
				stages,
				"llm_reasoning",
				"skipped",
				"GEMINI_API_KEY not set; using deterministic fallback ranking.",
			)
		report.recommendations = recs
		return report
	finally:
		if owns_session:
			db_session.close()
