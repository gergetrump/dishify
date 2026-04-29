"""End-to-end orchestration of the README pipeline.

	1. normalize  -> 2. hard filter (Postgres)  -> 3. vector retrieval (Qdrant)
	-> 4. rule-based scoring  -> 5. LLM reasoning

Each stage records its outcome **and** its latency in
``PipelineReport.stages`` so the API can return clear status to the caller
and we can degrade gracefully when optional dependencies (Gemini, vector
store, DB) are missing.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field

from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session

from ..clients.gemini import GeminiClient
from ..db import Recipe, SessionLocal, get_by_ids, hard_filter
from ..vectorstore import InMemoryVectorStore, QdrantVectorStore
from .explanation import Recommendation, explain
from .normalization import IngredientNormalizer
from .ranking import RankedCandidate, fallback_rank_without_vectors, score_candidates, take_top
from .retrieval import RetrievalUnavailable, retrieve_candidates

logger = logging.getLogger(__name__)


@dataclass
class StageReport:
	name: str
	status: str  # "ok" | "skipped" | "error" | "pending"
	detail: str | None = None
	latency_ms: float | None = None


@dataclass
class PipelineReport:
	normalized_ingredients: list[str]
	stages: list[StageReport] = field(default_factory=list)
	candidate_pool_size: int = 0
	retrieved_count: int = 0
	scored_count: int = 0
	recommendations: list[Recommendation] = field(default_factory=list)


@contextmanager
def _stage(stages: list[StageReport], name: str) -> Iterator[StageReport]:
	report = StageReport(name=name, status="pending")
	stages.append(report)
	started = time.perf_counter()
	try:
		yield report
	finally:
		report.latency_ms = round((time.perf_counter() - started) * 1000, 2)


def run_pipeline(
	ingredients: Sequence[str],
	profile: dict,
	*,
	top_k_retrieval: int = 50,
	top_k_explanation: int = 5,
	session: Session | None = None,
	gemini_client: GeminiClient | None = None,
	vector_store: InMemoryVectorStore | QdrantVectorStore | None = None,
) -> PipelineReport:
	stages: list[StageReport] = []
	client = gemini_client or GeminiClient()

	# --- Stage 2: normalization ---
	with _stage(stages, "normalize") as st:
		normalizer = IngredientNormalizer(client=client)
		normalized = normalizer.normalize(ingredients)
		st.status = "ok"
		st.detail = f"{len(normalized)} ingredients"
	report = PipelineReport(normalized_ingredients=normalized, stages=stages)

	if not normalized:
		with _stage(stages, "hard_filter") as st:
			st.status = "skipped"
			st.detail = "No ingredients to query."
		return report

	# --- Stage 3: hard filter -- needs DB ---
	owns_session = session is None
	try:
		db_session = session if session is not None else SessionLocal()
	except SQLAlchemyError as exc:
		logger.warning("DB unavailable: %s", exc, exc_info=True)
		with _stage(stages, "hard_filter") as st:
			st.status = "error"
			st.detail = f"DB unavailable: {exc}"
		return report

	try:
		with _stage(stages, "hard_filter") as st:
			try:
				pool: list[Recipe] = hard_filter(
					db_session,
					diet=profile.get("diet"),
					allergies=profile.get("allergies", []) or [],
				)
				report.candidate_pool_size = len(pool)
				st.status = "ok"
				st.detail = f"{len(pool)} recipes survived hard constraints"
			except OperationalError as exc:
				logger.warning("Hard filter DB error: %s", exc.orig, exc_info=True)
				st.status = "error"
				st.detail = f"DB query failed: {exc.orig}"
				return report

		if not pool:
			for name in ("vector_retrieval", "rule_based_scoring", "llm_reasoning"):
				with _stage(stages, name) as st:
					st.status = "skipped"
					st.detail = "Empty candidate pool"
			return report

		# --- Stage 4: vector retrieval ---
		ranked: list[RankedCandidate]
		with _stage(stages, "vector_retrieval") as st:
			try:
				candidates = retrieve_candidates(
					normalized,
					allowed_ids=[r.id for r in pool],
					top_k=top_k_retrieval,
					gemini_client=client,
					vector_store=vector_store,
				)
				report.retrieved_count = len(candidates)

				if not candidates:
					st.status = "ok"
					st.detail = "0 hits; falling back to overlap-only ranking."
					ranked = fallback_rank_without_vectors(pool, normalized, limit=top_k_retrieval)
				else:
					retrieved_recipes = get_by_ids(db_session, [c.recipe_id for c in candidates])
					ranked = score_candidates(candidates, retrieved_recipes, normalized)
					st.status = "ok"
					st.detail = f"{len(candidates)} hits"
			except RetrievalUnavailable as exc:
				logger.info("Retrieval skipped: %s", exc)
				st.status = "skipped"
				st.detail = str(exc)
				ranked = fallback_rank_without_vectors(pool, normalized, limit=top_k_retrieval)

		# --- Stage 5: scoring ---
		with _stage(stages, "rule_based_scoring") as st:
			report.scored_count = len(ranked)
			st.status = "ok"
			st.detail = f"{len(ranked)} scored"

		# --- Stage 6: LLM reasoning ---
		with _stage(stages, "llm_reasoning") as st:
			top = take_top(ranked, top_k_explanation)
			recs = explain(normalized, profile, top, gemini_client=client)
			report.recommendations = recs
			if client.is_configured:
				st.status = "ok"
				st.detail = f"{len(recs)} recommendations"
			else:
				st.status = "skipped"
				st.detail = "GEMINI_API_KEY not set; using deterministic fallback ranking."
		return report
	finally:
		if owns_session:
			db_session.close()
