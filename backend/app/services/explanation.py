"""Stage 6 -- final LLM reasoning.

The LLM only sees the top 5-10 ranked candidates. It returns ranked
recommendations with a short reason and any helpful substitutions.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import List, Optional, Sequence

from ..clients.gemini import GeminiClient, GeminiError
from .ranking import RankedCandidate


@dataclass
class Recommendation:
	recipe_id: int
	rank: int
	reason: str
	missing_ingredients: List[str]
	substitutions: List[str]


def _candidate_to_prompt_dict(c: RankedCandidate) -> dict:
	return {
		"recipe_id": c.recipe.id,
		"title": c.recipe.title,
		"ingredients": c.recipe.ingredients_clean,
		"available_ingredients": c.available_ingredients,
		"missing_ingredients": c.missing_ingredients,
		"diet": c.recipe.diet,
		"score": round(c.score, 4),
	}


def _build_prompt(
	user_ingredients: Sequence[str],
	profile: dict,
	candidates: Sequence[RankedCandidate],
) -> str:
	return (
		"You are a cooking assistant ranking recipe candidates for a user.\n"
		"Pick the best matches based on which ingredients the user already has, "
		"the user's profile, and how few additional ingredients they would need.\n"
		"For each pick, write a one-sentence reason and propose pragmatic substitutions "
		"for missing items when reasonable. Do not invent recipes or ingredients.\n"
		"Return STRICT JSON with this shape:\n"
		'{"recommendations": [{"recipe_id": int, "rank": int, "reason": str, '
		'"missing_ingredients": [str], "substitutions": [str]}]}\n'
		f"User ingredients: {json.dumps(list(user_ingredients))}\n"
		f"User profile: {json.dumps(profile)}\n"
		f"Candidates: {json.dumps([_candidate_to_prompt_dict(c) for c in candidates])}\n"
	)


def explain(
	user_ingredients: Sequence[str],
	profile: dict,
	candidates: Sequence[RankedCandidate],
	*,
	gemini_client: Optional[GeminiClient] = None,
) -> List[Recommendation]:
	"""Ask Gemini to rank/justify candidates. Falls back to deterministic
	ranking if the model is unreachable."""

	if not candidates:
		return []

	client = gemini_client or GeminiClient()
	if not client.is_configured:
		return _deterministic_recommendations(candidates)

	try:
		payload = client.generate_json(
			_build_prompt(user_ingredients, profile, candidates),
			temperature=0.2,
		)
	except GeminiError:
		return _deterministic_recommendations(candidates)

	raw_recs = payload.get("recommendations") if isinstance(payload, dict) else None
	if not isinstance(raw_recs, list):
		return _deterministic_recommendations(candidates)

	by_id = {c.recipe.id: c for c in candidates}
	recs: list[Recommendation] = []
	for idx, item in enumerate(raw_recs):
		if not isinstance(item, dict):
			continue
		try:
			recipe_id = int(item["recipe_id"])
		except (KeyError, TypeError, ValueError):
			continue
		if recipe_id not in by_id:
			continue
		fallback = by_id[recipe_id]
		recs.append(
			Recommendation(
				recipe_id=recipe_id,
				rank=int(item.get("rank", idx + 1)),
				reason=str(item.get("reason", "")).strip(),
				missing_ingredients=[str(x) for x in item.get("missing_ingredients", []) or fallback.missing_ingredients],
				substitutions=[str(x) for x in item.get("substitutions", []) or []],
			)
		)

	if not recs:
		return _deterministic_recommendations(candidates)
	return recs


def _deterministic_recommendations(candidates: Sequence[RankedCandidate]) -> List[Recommendation]:
	return [
		Recommendation(
			recipe_id=c.recipe.id,
			rank=idx + 1,
			reason=(
				f"You already have {len(c.available_ingredients)} of "
				f"{len(c.available_ingredients) + len(c.missing_ingredients)} ingredients."
			),
			missing_ingredients=c.missing_ingredients,
			substitutions=[],
		)
		for idx, c in enumerate(candidates)
	]
